import http from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { openBrowser } from './browser.mjs';

const ROOT = path.dirname(fileURLToPath(import.meta.url));
if (existsSync(path.join(ROOT, '.env'))) process.loadEnvFile(path.join(ROOT, '.env'));
const dev = process.argv.includes('--dev');
const port = Number(process.env.PORT || 8788);
const host = '127.0.0.1';
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
function validate(data, video) {
  if (!data || typeof data.prompt !== 'string' || !data.prompt.trim() || data.prompt.length > 12000) throw Object.assign(new Error('Prompt cần có 1–12.000 ký tự.'), { status: 400 });
  if (!Number.isInteger(data.accountId) || data.accountId < 1 || data.accountId > 10) throw Object.assign(new Error('accountId cần nằm trong 1–10.'), { status: 400 });
  if (!video) return;
  if (!['Omni 1.1 Flash', 'Veo 3.1 - Lite', 'Veo 3.1 - Fast'].includes(data.model)) throw Object.assign(new Error('MODEL_UNSUPPORTED: Model không hợp lệ.'), { status: 400 });
  if (!['16:9', '9:16'].includes(data.aspectRatio) || ![4, 6, 8, 10].includes(data.duration) || !['360p', '720p'].includes(data.resolution) || (data.model !== 'Omni 1.1 Flash' && (data.duration !== 8 || data.resolution !== '720p'))) throw Object.assign(new Error('Thiết lập mô hình, thời lượng hoặc độ phân giải không hợp lệ.'), { status: 400 });
  if (data.image && (!['image/png', 'image/jpeg', 'image/webp'].includes(data.image.mimeType) || typeof data.image.imageBytes !== 'string' || !/^[A-Za-z0-9+/]+={0,2}$/.test(data.image.imageBytes) || data.image.imageBytes.length > 11200000)) throw Object.assign(new Error('Ảnh cần là PNG, JPEG hoặc WebP base64, tối đa 8 MB.'), { status: 400 });
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
  if (req.method === 'GET' && pathname === '/api/status') return json(res, 200, { museConfigured: Boolean(process.env.MUSE_ADAPTER_URL), busy, credit: null, gpu: null });
  if (req.method !== 'POST') return json(res, 405, { error: 'Method not allowed' });
  if (req.headers.origin && req.headers.origin !== `http://${req.headers.host}`) return json(res, 403, { error: 'Origin không được phép.' });
  if (!req.headers['content-type']?.startsWith('application/json')) return json(res, 415, { error: 'Cần Content-Type application/json.' });
  if (!['/api/video', '/api/text'].includes(pathname)) return json(res, 404, { error: 'API không tồn tại.' });
  let acquired = false;
  const abort = new AbortController();
  res.on('close', () => abort.abort());
  const timeout = setTimeout(() => abort.abort(new Error('TIMEOUT: Hết 10 phút chờ. Yêu cầu đã gửi có thể vẫn được tính phí.')), 10 * 60 * 1000);
  try {
    const data = await body(req);
    validate(data, pathname === '/api/video');
    adapterURL(pathname === '/api/video' ? '/video' : '/text');
    if (busy) return json(res, 409, { error: 'Đang có một yêu cầu AI. Vui lòng đợi tác vụ hiện tại kết thúc.' });
    busy = acquired = true;
    const result = await callAdapter(pathname === '/api/video' ? '/video' : '/text', {
      accountId: data.accountId, prompt: data.prompt,
      ...(pathname === '/api/video' ? { modelDisplayName: data.model, aspectRatio: data.aspectRatio,
        durationSeconds: data.duration, resolution: data.resolution,
        referenceImage: data.image ? { base64: data.image.imageBytes, mimeType: data.image.mimeType } : undefined } : {})
    }, abort.signal);
    if (pathname === '/api/video' && (typeof result.base64 !== 'string' || !result.base64 || !/^[A-Za-z0-9+/\s]+={0,2}$/.test(result.base64) || !['video/mp4', 'video/webm', 'video/quicktime'].includes(result.mimeType))) throw new Error('MUSE_RESPONSE_INVALID: Cần {base64, mimeType} video hợp lệ từ adapter.');
    if (pathname === '/api/text' && (typeof result.text !== 'string' || !result.text.trim())) throw new Error('MUSE_RESPONSE_INVALID: Cần {text} không trống từ adapter.');
    return json(res, 200, pathname === '/api/video' ? { base64: result.base64, mimeType: result.mimeType } : { text: result.text });
  } catch (error) { json(res, Number.isInteger(error.status) && error.status >= 400 && error.status <= 599 ? error.status : 502, { error: safeError(error) }); }
  finally { clearTimeout(timeout); if (acquired) busy = false; }
}
const mime = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.mp4': 'video/mp4', '.ico': 'image/x-icon' };
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
  if (!process.env.MUSE_ADAPTER_URL) console.log('Chua ket noi nguon tao video AI. Giao dien van hoat dong; xem muc Ket noi trong tool.');
  if (process.argv.includes('--open')) openBrowser(url);
});
server.on('error', error => {
  console.error(error.code === 'EADDRINUSE' ? `Cong ${port} dang duoc su dung. Neu tool da mo, truy cap http://${host}:${port}; neu chua, dat PORT khac trong .env.` : error.message);
  process.exitCode = 1;
});
for (const name of ['SIGINT', 'SIGTERM']) process.on(name, () => { server.close(); vite?.close(); process.exit(0); });
