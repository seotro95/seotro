import type { Mode, Reference, Settings, MediaResult } from './core.ts';
import { reserveDownloadNumbers, formatDownloadNumber } from './download-sequence.ts';

type ResponseMedia = { base64: string; mimeType: string; metadata?: { duration?: number; width: number; height: number } };
type RequestContext = { batchId: string; sceneId: number; accountId?: number; accountMode?: Settings['accountMode'] };
declare global {
  interface Window { museTransport?: { request(id: string, endpoint: string, data: unknown): Promise<{ ok: boolean; body: any }>; cancel(id: string): void; export?(action: string, data?: unknown): Promise<any>; onSessionRefresh?(callback: () => void): () => void }; showDirectoryPicker?: () => Promise<ExportDirectory> }
}
type ExportDirectory = { name: string; getDirectoryHandle(name: string, options?: { create?: boolean }): Promise<ExportDirectory>; getFileHandle(name: string, options?: { create?: boolean }): Promise<{ createWritable(): Promise<{ write(blob: Blob): Promise<void>; close(): Promise<void> }> }> };
let webExportDirectory: ExportDirectory | null = null;
export async function chooseExportDirectory() {
  if (window.museTransport?.export) return window.museTransport.export('choose');
  if (!window.showDirectoryPicker) throw new Error('Mở Muse AI Studio.exe để lưu cả bộ vào thư mục trên máy.');
  try { webExportDirectory = await window.showDirectoryPicker(); return { cancelled: false, name: webExportDirectory.name }; }
  catch (error) { if ((error as Error).name === 'AbortError') return { cancelled: true }; throw error; }
}
async function api(path: string, data?: unknown, signal?: AbortSignal) {
  const transport = window.museTransport;
  if (transport && ['/api/video', '/api/image', '/api/text'].includes(path)) {
    signal?.throwIfAborted();
    const id = crypto.randomUUID();
    const cancel = () => transport.cancel(id);
    signal?.addEventListener('abort', cancel, { once: true });
    try {
      const result = await transport.request(id, path, data);
      signal?.throwIfAborted();
      if (!result.ok) throw new Error(result.body?.error || 'DESKTOP_REQUEST_FAILED');
      return result.body;
    } finally { signal?.removeEventListener('abort', cancel); }
  }
  const response = await fetch(path, { method: data === undefined ? 'GET' : 'POST',
    headers: data === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: data === undefined ? undefined : JSON.stringify(data), signal });
  const result = await response.json().catch(() => ({ error: `HTTP ${response.status}: phản hồi không phải JSON.` }));
  if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
  return result;
}
export async function readImage(file: File): Promise<Reference> {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) throw new Error('Chọn ảnh PNG, JPG hoặc WebP.');
  if (file.size > 8 * 1024 * 1024) throw new Error('Ảnh tham chiếu tối đa 8 MB.');
  const url = await new Promise<string>((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(String(reader.result)); reader.onerror = () => reject(new Error('Không đọc được ảnh.')); reader.readAsDataURL(file); });
  await new Promise<void>((resolve, reject) => { const img = new Image(); img.onload = () => resolve(); img.onerror = () => reject(new Error('Tệp ảnh bị hỏng hoặc không hỗ trợ.')); img.src = url; });
  return { id: crypto.randomUUID(), name: file.name, url, base64: url.split(',')[1], mimeType: file.type };
}
async function mediaResult(kind: Settings['output'], result: ResponseMedia, settings: Settings): Promise<MediaResult> {
  const allowed = kind === 'image' ? ['image/png', 'image/jpeg', 'image/webp'] : ['video/mp4', 'video/webm', 'video/quicktime'];
  if (!result || typeof result.base64 !== 'string' || !result.base64 || !allowed.includes(result.mimeType)) throw new Error('MUSE_MEDIA_INVALID: Muse chưa trả về tệp ảnh/video hợp lệ.');
  let bytes: Uint8Array;
  const clean = result.base64.replace(/^data:[^;]+;base64,/, '').replace(/\s/g, '');
  try { bytes = Uint8Array.from(atob(clean), c => c.charCodeAt(0)); } catch { throw new Error('MUSE_MEDIA_INVALID: Dữ liệu base64 không hợp lệ.'); }
  const url = URL.createObjectURL(new Blob([bytes.slice().buffer], { type: result.mimeType }));
  let metadata = result.metadata && [result.metadata.width, result.metadata.height].every(n => Number.isFinite(n) && n > 0) ? result.metadata : undefined;
  if (kind === 'image') {
    try { metadata = await new Promise((resolve, reject) => { const img = new Image(); img.onload = () => resolve({ width: img.naturalWidth, height: img.naturalHeight }); img.onerror = reject; img.src = url; }); }
    catch { URL.revokeObjectURL(url); throw new Error('MUSE_IMAGE_INVALID: Tệp ảnh trả về không giải mã được.'); }
  }
  return { kind, base64: clean, mimeType: result.mimeType, url, demo: settings.mode === 'demo', metadata,
    requestedResolution: kind === 'image' ? settings.imageResolution : settings.resolution, aspectRatio: settings.aspectRatio };
}
export function releaseVideo(media?: MediaResult) { if (!media?.savedId && media?.url.startsWith('blob:')) URL.revokeObjectURL(media.url); }
async function referencePayload(reference: Reference, signal: AbortSignal) {
  if ((reference.base64?.length || 0) <= 8 * 1024 * 1024 * 4 / 3) return { imageBytes: reference.base64, mimeType: reference.mimeType, compressed: false };
  const img = await new Promise<HTMLImageElement>((resolve, reject) => { const image = new Image(); image.onload = () => resolve(image); image.onerror = reject; image.src = reference.url; });
  signal.throwIfAborted();
  const canvas = document.createElement('canvas'); canvas.width = img.naturalWidth; canvas.height = img.naturalHeight;
  canvas.getContext('2d')!.drawImage(img, 0, 0);
  for (const quality of [0.9, 0.75, 0.6]) {
    signal.throwIfAborted();
    const encoded = canvas.toDataURL('image/webp', quality);
    const data = encoded.split(',')[1];
    const mimeType = encoded.slice(5, encoded.indexOf(';'));
    if (data.length <= 8 * 1024 * 1024 * 4 / 3) return { imageBytes: data, mimeType, compressed: true };
  }
  throw new Error('REFERENCE_TOO_LARGE: Chưa nén được ảnh đầu vào xuống 8 MB; hãy dùng ảnh nhỏ hơn. Bản ảnh gốc vẫn được giữ.');
}
async function demoMedia(kind: Settings['output'], signal: AbortSignal): Promise<ResponseMedia> {
  await new Promise<void>((resolve, reject) => {
    const finish = () => { signal.removeEventListener('abort', abort); resolve(); };
    const timeout = setTimeout(finish, 550);
    const abort = () => { clearTimeout(timeout); reject(new DOMException('Đã dừng', 'AbortError')); };
    signal.addEventListener('abort', abort, { once: true });
  });
  const response = await fetch(kind === 'image' ? '/demo-image.png' : '/demo.mp4', { signal });
  if (!response.ok) throw new Error('Không tìm thấy tệp kiểm thử đi kèm.');
  const bytes = new Uint8Array(await response.arrayBuffer());
  let binary = ''; for (const byte of bytes) binary += String.fromCharCode(byte);
  return { base64: btoa(binary), mimeType: kind === 'image' ? 'image/png' : 'video/mp4' };
}
async function generate(kind: Settings['output'], prompt: string, reference: Reference | null, settings: Settings, signal: AbortSignal, context?: RequestContext) {
  signal.throwIfAborted();
  const fullPrompt = [prompt.trim(), settings.modifier.trim()].filter(Boolean).join('\n\n');
  if (!prompt.trim()) throw new Error('Hãy nhập prompt cho cảnh trước khi tạo.');
  if (kind === 'video' && settings.videoInput === 'image' && !reference) throw new Error('SOURCE_IMAGE_REQUIRED: Chọn ảnh đầu vào hoặc dùng ảnh vừa tạo để làm video.');
  const sendReference = reference && (settings.r2v || (kind === 'video' && settings.videoInput === 'image'));
  if (sendReference && !reference.base64) throw new Error('Ảnh đầu vào chưa có dữ liệu để gửi đến Muse.');
  const prepared = sendReference && settings.mode !== 'demo' ? await referencePayload(reference, signal) : null;
  const result = settings.mode === 'demo' ? await demoMedia(kind, signal) : await api(`/api/${kind}`, {
    accountId: 1, prompt: fullPrompt, ...context, aspectRatio: settings.aspectRatio, resolution: kind === 'image' ? settings.imageResolution : settings.resolution,
    characterLock: settings.r2v, ...(kind === 'video' ? { model: settings.model, duration: settings.duration, sourceMode: settings.videoInput } : {}),
    image: prepared ? { imageBytes: prepared.imageBytes, mimeType: prepared.mimeType } : undefined
  }, signal);
  signal.throwIfAborted();
  return { ...await mediaResult(kind, result, settings), referenceCompressed: prepared?.compressed || false };
}
export const generateVideo = (prompt: string, reference: Reference | null, settings: Settings, signal: AbortSignal, context?: RequestContext) => generate('video', prompt, reference, settings, signal, context);
export const generateImage = (prompt: string, reference: Reference | null, settings: Settings, signal: AbortSignal, context?: RequestContext) => generate('image', prompt, reference, settings, signal, context);
export async function enhancePrompt(prompt: string, mode: Mode, signal: AbortSignal, context?: RequestContext): Promise<string> {
  if (mode === 'demo') throw new Error('Chế độ kiểm thử không có AI Enhance. Kết nối Muse AI để trau chuốt thật.');
  const instruction = `Rewrite this scene as one concise cinematic visual prompt in English. Preserve the characters, action and narrative. Add specific composition and lighting. Return only the rewritten prompt, no headings. Scene:\n${prompt}`;
  const result = await api('/api/text', { prompt: instruction, accountId: 1, ...context }, signal);
  signal.throwIfAborted();
  if (typeof result.text !== 'string' || !result.text.trim()) throw new Error('AI không trả về prompt văn bản.');
  return result.text.trim().slice(0, 8000);
}
async function mediaFile(media: MediaResult, id: number) {
  if (media.kind === 'image') {
    const image = await new Promise<HTMLImageElement>((resolve, reject) => { const value = new Image(); value.onload = () => resolve(value); value.onerror = () => reject(new Error('Không giải mã được ảnh để tải xuống.')); value.src = media.url; });
    const canvas = document.createElement('canvas'); canvas.width = image.naturalWidth; canvas.height = image.naturalHeight;
    canvas.getContext('2d')!.drawImage(image, 0, 0);
    const blob = await new Promise<Blob>((resolve, reject) => canvas.toBlob(value => value ? resolve(value) : reject(new Error('Không xuất được PNG.')), 'image/png'));
    return { prefix: `${media.demo ? 'kiem-thu-' : ''}image`, extension: 'png', blob };
  }
  const ext = ({ 'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp', 'video/webm': 'webm', 'video/quicktime': 'mov' } as Record<string, string>)[media.mimeType] || 'mp4';
  const response = await fetch(media.url);
  if (!response.ok) throw new Error(`Không đọc được kết quả cảnh ${id} để tải xuống.`);
  return { prefix: `${media.demo ? 'kiem-thu-' : ''}video`, extension: ext, blob: await response.blob() };
}
function numberedFilename(file: { prefix: string; extension: string }, id: number, number: bigint, namespace: string) {
  return `${file.prefix}-${formatDownloadNumber(number)}-scene-${String(id).padStart(2, '0')}-${namespace}.${file.extension}`;
}
function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}
export async function downloadVideo(media: MediaResult, id: number) {
  const file = await mediaFile(media, id);
  const range = await reserveDownloadNumbers(1);
  downloadBlob(file.blob, numberedFilename(file, id, range.first, range.namespace));
}
export async function downloadMediaBatch(items: { media: MediaResult; id: number }[], kind: Settings['output']) {
  if (!items.length) throw new Error('Chưa có kết quả để tải.');
  const native = window.museTransport?.export;
  const destination = native ? await native('ensure') : webExportDirectory ? { cancelled: false } : await chooseExportDirectory();
  if (destination.cancelled) return { cancelled: true as const };
  const files = [];
  for (const item of items) files.push(await mediaFile(item.media, item.id));
  const range = await reserveDownloadNumbers(items.length);
  const first = formatDownloadNumber(range.first); const last = formatDownloadNumber(range.last);
  const label = `Muse-${kind === 'image' ? 'Images' : 'Videos'}-${items.length}-${first}-${last}-${range.namespace}`;
  let session: { id: string; name: string } | undefined;
  try {
    let directory: ExportDirectory | undefined;
    if (native) session = await native('begin', { kind, count: items.length, first, last, namespace: range.namespace });
    else {
      for (let suffix=0;suffix<100;suffix++) {
        const candidate=label+(suffix?`-${suffix+1}`:'');
        try { await webExportDirectory!.getDirectoryHandle(candidate); }
        catch (error) {
          if ((error as Error).name!=='NotFoundError') throw error;
          directory=await webExportDirectory!.getDirectoryHandle(candidate,{create:true});break;
        }
      }
      if (!directory) throw new Error('Chưa tạo được thư mục mới cho bộ kết quả.');
    }
    for (const [index,file] of files.entries()) {
      const name=numberedFilename(file,items[index].id,range.first+BigInt(index),range.namespace);
      if (native) await native('write',{id:session!.id,name,bytes:await file.blob.arrayBuffer()});
      else {
        const handle=await directory!.getFileHandle(name,{create:true});
        const stream=await handle.createWritable();await stream.write(file.blob);await stream.close();
      }
    }
    const saved=native?await native('finish',session!.id):{directory:directory!.name,count:files.length};
    return { cancelled:false as const,first,last,folder:saved.directory,count:saved.count };
  } catch (error) { if (native&&session) await native('abort',session.id).catch(()=>{}); throw error; }
}
export const providerStatus = () => api('/api/status');
export const accountAction = (action: 'connect' | 'check' | 'close' | 'composer' | 'concurrency' | 'import' | 'select', data: Record<string, unknown> = {}) => api(`/api/account/${action}`, data);
