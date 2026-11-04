import http from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { openBrowser } from './browser.mjs';
import { MuseBrowser } from './muse-browser.mjs';

const ROOT = path.dirname(fileURLToPath(import.meta.url));
if (existsSync(path.join(ROOT, '.env'))) process.loadEnvFile(path.join(ROOT, '.env'));
const dev = process.argv.includes('--dev');
const port = Number(process.env.PORT || 8788);
const host = '127.0.0.1';
const transport = process.env.MUSE_TRANSPORT || (process.env.MUSE_ADAPTER_URL ? 'adapter' : 'browser');
if (!['browser', 'adapter'].includes(transport)) throw new Error('MUSE_TRANSPORT must be browser or adapter.');
const muse = transport === 'browser' ? new MuseBrowser({ profileRoot: path.resolve(process.env.MUSE_PROFILE_ROOT || path.join(ROOT, '.data', 'muse-accounts')), accountProfile: process.env.MUSE_ACCOUNT_PROFILE }) : null;
const MAX_BODY = 12 * 1024 * 1024;
let busy = false;
const vite = dev ? await (await import('vite')).createServer({ root: ROOT, server: { middlewareMode: true, hmr: false } }) : null;
const json = (res, status, value) => { if (!res.destroyed) { res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' }); res.end(JSON.stringify(value)); } };
async function body(req) {
  let size = 0;
  const chunks = [];
  for await (const chunk of req) { size += chunk.length;
    if (size > MAX_BODY) throw Object.assign(new Error('Yêu cầu vượt giới hạn 12 MB.'), { status: 413 });
    chunks.push(chunk);
  }
  try { return JSON.parse(Buffer.concat(chunks).toString()); }
  catch { throw Object.assign(new Error('JSON không hợp lệ.'), { status: 400 }); }
}
function validate(data, kind) {
  const invalid = message => { throw Object.assign(new Error(message), { status: 400 }); };
  if (!data || typeof data.prompt !== 'string' || !data.prompt.trim() || data.prompt.length > 12000) invalid('Prompt cần có 1–12.000 ký tự.');
  if (data.accountId !== 1) invalid('ACCOUNT_INVALID: Chỉ sử dụng tài khoản Muse duy nhất (accountId=1).');
  if (kind === 'text') return;
  if (!['16:9', '9:16'].includes(data.aspectRatio)) invalid('Tỉ lệ khung hình không hợp lệ.');
  if (kind === 'video') {
    if (!['Omni 1.1 Flash', 'Veo 3.1 - Lite', 'Veo 3.1 - Fast'].includes(data.model)) invalid('MODEL_UNSUPPORTED: Model không hợp lệ.');
    if (![4, 6, 8, 10].includes(data.duration) || !['360p', '720p', '1080p', '2k', '4k'].includes(data.resolution) || (data.model !== 'Omni 1.1 Flash' && data.duration !== 8)) invalid('Thiết lập thời lượng hoặc độ phân giải không hợp lệ.');
    if (data.sourceMode !== undefined && !['text', 'image'].includes(data.sourceMode)) invalid('Chế độ nguồn video không hợp lệ.');
    if (data.sourceMode === 'image' && !data.image) invalid('SOURCE_IMAGE_REQUIRED: Chọn ảnh đầu vào trước khi tạo video từ ảnh.');
  } else if (!['2k', '4k'].includes(data.resolution)) invalid('Ảnh hỗ trợ mức yêu cầu 2K hoặc 4K.');
  if (data.characterLock !== undefined && typeof data.characterLock !== 'boolean') invalid('Tùy chọn đồng nhất nhân vật không hợp lệ.');
  if (data.image && (!['image/png', 'image/jpeg', 'image/webp'].includes(data.image.mimeType) || typeof data.image.imageBytes !== 'string' || !/^[A-Za-z0-9+/]+={0,2}$/.test(data.image.imageBytes) || data.image.imageBytes.length > 11200000)) invalid('Ảnh cần là PNG, JPEG hoặc WebP base64, tối đa 8 MB.');
}
function safeError(error) {
  let text = error instanceof Error ? error.message : String(error);
  const token = process.env.MUSE_ADAPTER_TOKEN;
  if (token) text = text.split(token).join('[REDACTED]');
  return text.replace(/(Bearer\s+)[^\s"']+/gi, '$1[REDACTED]').slice(0, 4000);
}
function adapterURL(endpoint) {
  if (!process.env.MUSE_ADAPTER_URL) throw Object.assign(new Error('MUSE_NOT_CONFIGURED: Chưa có kết nối Muse AI. Cần API hoặc adapter đã xác thực tài khoản. Xem README.'), { status: 503 });
  const url = new URL(process.env.MUSE_ADAPTER_URL.replace(/\/$/, '') + endpoint);
  if (url.username || url.password || (url.protocol !== 'https:' && !(url.protocol === 'http:' && ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)))) throw Object.assign(new Error('Adapter cần URL HTTPS, hoặc HTTP trên loopback. Không đặt thông tin đăng nhập trong URL.'), { status: 503 });
  return url;
}
async function callAdapter(endpoint, data, signal) {
  const response = await fetch(adapterURL(endpoint), { method: 'POST', redirect: 'error',
    headers: { 'Content-Type': 'application/json', ...(process.env.MUSE_ADAPTER_TOKEN ? { Authorization: `Bearer ${process.env.MUSE_ADAPTER_TOKEN}` } : {}) },
    body: JSON.stringify(data), signal });
  if (Number(response.headers.get('content-length')) > 150 * 1024 * 1024) throw new Error('VIDEO_TOO_LARGE: Phản hồi vượt 150 MB.');
  const reader = response.body.getReader();
  const chunks = [];
  let size = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.length;
    if (size > 150 * 1024 * 1024) { await reader.cancel(); throw new Error('VIDEO_TOO_LARGE: Phản hồi vượt 150 MB.'); }
    chunks.push(Buffer.from(value));
  }
  let result;
  try { result = JSON.parse(Buffer.concat(chunks).toString()); }
  catch { throw new Error(`MUSE_RESPONSE_INVALID: HTTP ${response.status}, adapter không trả về JSON.`); }
  if (!response.ok) throw Object.assign(new Error(typeof result.error === 'string' ? result.error : `MUSE_HTTP_${response.status}`), { status: response.status });
  return result;
}
async function api(req, res, pathname) {
  if (req.method === 'GET' && pathname === '/api/status') {
    if (muse && !busy) await muse.refreshActive();
    return json(res, 200, { museConfigured: Boolean(muse || process.env.MUSE_ADAPTER_URL), transport, accounts: muse?.snapshot() || [], busy, credit: null, gpu: null });
  }
  if (req.method !== 'POST') return json(res, 405, { error: 'Method not allowed' });
  if (req.headers.origin && req.headers.origin !== `http://${req.headers.host}`) return json(res, 403, { error: 'Origin không được phép.' });
  if (!req.headers['content-type']?.startsWith('application/json')) return json(res, 415, { error: 'Cần Content-Type application/json.' });
  const accountRoute = pathname.match(/^\/api\/account\/(connect|check|close)$/);
  const legacyAccountRoute = pathname.match(/^\/api\/accounts\/(\d+)\/(connect|check|close)$/);
  if (!['/api/video', '/api/image', '/api/text'].includes(pathname) && !accountRoute && !legacyAccountRoute) return json(res, 404, { error: 'API không tồn tại.' });
  let acquired = false;
  const abort = new AbortController();
  res.on('close', () => abort.abort());
  const timeout = setTimeout(() => abort.abort(new Error('TIMEOUT: Hết 10 phút chờ. Yêu cầu đã gửi có thể vẫn được tính phí.')), 10 * 60 * 1000);
  try {
    const data = await body(req);
    if (accountRoute || legacyAccountRoute) {
      const accountId = legacyAccountRoute ? Number(legacyAccountRoute[1]) : 1;
      const action = accountRoute ? accountRoute[1] : legacyAccountRoute[2];
      if (accountId !== 1) return json(res, 400, { error: 'ACCOUNT_INVALID: Bản này chỉ dùng một tài khoản Muse.' });
      if (!muse) return json(res, 409, { error: 'Tài khoản đang do adapter riêng quản lý. Chọn MUSE_TRANSPORT=browser để đăng nhập bằng Chrome/Edge.' });
      if (busy) return json(res, 409, { error: 'Đang có tác vụ. Đợi hoàn tất trước khi đổi cửa sổ tài khoản.' });
      muse.account(accountId);
      busy = acquired = true;
      if (action === 'close') { if (muse.active?.id === accountId) await muse.close(); }
      else await muse.connect(accountId);
      return json(res, 200, { accounts: muse.snapshot() });
    }
    const kind = pathname === '/api/video' ? 'video' : pathname === '/api/image' ? 'image' : 'text';
    validate(data, kind);
    const endpoint = `/${kind}`;
    if (!muse) adapterURL(endpoint);
    if (busy) return json(res, 409, { error: 'Đang có một yêu cầu AI. Vui lòng đợi tác vụ hiện tại kết thúc.' });
    busy = acquired = true;
    const useImage = data.image && (data.characterLock !== false || (kind === 'video' && data.sourceMode === 'image'));
    const payload = { accountId: data.accountId, prompt: data.prompt,
      ...(kind !== 'text' ? { aspectRatio: data.aspectRatio, resolution: data.resolution, characterLock: data.characterLock !== false,
        referenceImage: useImage ? { base64: data.image.imageBytes, mimeType: data.image.mimeType } : undefined } : {}),
      ...(kind === 'video' ? { modelDisplayName: data.model, durationSeconds: data.duration, sourceMode: data.sourceMode || 'text' } : {})
    };
    const result = muse ? await (kind === 'video' ? muse.generateVideo(payload, abort.signal) : kind === 'image' ? muse.generateImage(payload, abort.signal) : muse.generateText(payload, abort.signal)) : await callAdapter(endpoint, payload, abort.signal);
    const allowedMime = kind === 'image' ? ['image/png', 'image/jpeg', 'image/webp'] : ['video/mp4', 'video/webm', 'video/quicktime'];
    if (kind !== 'text' && (typeof result.base64 !== 'string' || !result.base64 || !/^[A-Za-z0-9+/\s]+={0,2}$/.test(result.base64) || !allowedMime.includes(result.mimeType))) throw new Error('MUSE_RESPONSE_INVALID: Cần dữ liệu base64 và MIME của tệp ảnh/video hợp lệ.');
    if (kind === 'text' && (typeof result.text !== 'string' || !result.text.trim())) throw new Error('MUSE_RESPONSE_INVALID: Cần {text} không trống.');
    const metadata = result.metadata && Number.isFinite(result.metadata.width) && Number.isFinite(result.metadata.height) ? result.metadata : undefined;
    return json(res, 200, kind !== 'text' ? { base64: result.base64, mimeType: result.mimeType, ...(metadata ? { metadata } : {}) } : { text: result.text });
  } catch (error) { json(res, Number.isInteger(error.status) && error.status >= 400 && error.status <= 599 ? error.status : 502, { error: safeError(error) }); }
  finally { clearTimeout(timeout); if (acquired) busy = false; }
}
const mime = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.mp4': 'video/mp4', '.png': 'image/png', '.ico': 'image/x-icon' };
const server = http.createServer(async (req, res) => {
  if (!['127.0.0.1', 'localhost'].includes((req.headers.host || '').split(':')[0])) return json(res, 403, { error: 'Chỉ hỗ trợ truy cập cục bộ.' });
  let pathname;
  try { pathname = decodeURIComponent(new URL(req.url, `http://${host}`).pathname); }
  catch { return json(res, 400, { error: 'URL không hợp lệ.' }); }
  if (pathname.startsWith('/api/')) return api(req, res, pathname);
  if (vite) return vite.middlewares(req, res);
  if (!['GET', 'HEAD'].includes(req.method)) return json(res, 405, { error: 'Method not allowed' });
  const root = path.join(ROOT, 'dist');
  let file = path.resolve(root, '.' + pathname);
  if (!file.startsWith(root + path.sep) && file !== root) return json(res, 403, { error: 'Forbidden' });
  if (pathname === '/') file = path.join(root, 'index.html');
  try {
    if (!(await stat(file)).isFile()) throw new Error('Not a file');
    const content = await readFile(file);
    res.writeHead(200, { 'Content-Type': mime[path.extname(file)] || 'application/octet-stream', 'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-cache' });
    res.end(req.method === 'HEAD' ? undefined : content);
  } catch { json(res, 404, { error: 'Không tìm thấy tệp. Chạy npm run build trước npm start.' }); }
});
server.requestTimeout = 12 * 60 * 1000;
server.listen(port, host, () => {
  const url = `http://${host}:${server.address().port}`;
  console.log(`Muse Studio: ${url} · ${dev ? 'development' : 'production'}`);
  console.log('Giu cua so nay mo khi su dung. Ctrl+C chi dung khi muon tat tool.');
  console.log(transport === 'browser' ? 'Ket noi Muse: bam Tai khoan Muse va dang nhap mot lan de tao ca 10 anh/video.' : 'Ket noi Muse qua adapter rieng.');
  if (process.argv.includes('--open')) openBrowser(url);
});
server.on('error', error => {
  console.error(error.code === 'EADDRINUSE' ? `Cong ${port} dang duoc su dung. Neu tool da mo, truy cap http://${host}:${port}; neu chua, dat PORT khac trong .env.` : error.message);
  process.exitCode = 1;
});
let stopping = false;
for (const name of ['SIGINT', 'SIGTERM']) process.on(name, async () => {
  if (stopping) return;
  stopping = true;
  server.close();
  const timer = setTimeout(() => process.exit(0), 5000);
  await muse?.close(); await vite?.close(); clearTimeout(timer); process.exit(0);
});
