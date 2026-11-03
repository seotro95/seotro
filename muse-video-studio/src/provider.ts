import type { Mode, Reference, Settings, VideoResult } from './core.ts';

type FlowMedia = { mediaId: string; url?: string; name?: string };
type FlowVideo = { base64: string; mimeType?: string };
export interface FlowSDK {
  media: { select: (options: { filter: 'image' }) => Promise<FlowMedia | FlowMedia[] | null> };
  generate: {
    video: (options: { prompt: string; modelDisplayName: string; referenceImageMediaIds: string[]; aspectRatio: string; durationSeconds: number; resolution: string }) => Promise<FlowVideo>;
    text: (options: { prompt: string }) => Promise<string | { text: string }>;
  };
  download: (options: { base64: string; mimeType: string; filename: string }) => Promise<void>;
}
declare global { interface Window { Flow?: FlowSDK } }
export const hasFlow = () => Boolean(window.Flow?.generate?.video && window.Flow?.media?.select);

async function api(path: string, data?: unknown, signal?: AbortSignal) {
  const response = await fetch(path, { method: data === undefined ? 'GET' : 'POST',
    headers: data === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: data === undefined ? undefined : JSON.stringify(data), signal });
  const result = await response.json().catch(() => ({ error: `HTTP ${response.status}: phản hồi không phải JSON.` }));
  if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
  return result;
}
function requireFlow(): FlowSDK {
  if (!hasFlow()) throw new Error('FLOW_UNAVAILABLE: Không tìm thấy Flow SDK tương thích trong trang hiện tại.');
  return window.Flow!;
}
async function waitForSDK<T>(request: Promise<T>, signal: AbortSignal): Promise<T> {
  signal.throwIfAborted();
  return new Promise<T>((resolve, reject) => {
    const abort = () => reject(new DOMException('Đã dừng chờ SDK', 'AbortError'));
    signal.addEventListener('abort', abort, { once: true });
    request.then(value => { signal.removeEventListener('abort', abort); resolve(value); }, error => { signal.removeEventListener('abort', abort); reject(error); });
  });
}
export async function selectFlowImage(): Promise<Reference | null> {
  const selected = await requireFlow().media.select({ filter: 'image' });
  const media = Array.isArray(selected) ? selected[0] : selected;
  if (!media) return null;
  if (typeof media.mediaId !== 'string' || !media.mediaId) throw new Error('SDK_MEDIA_FORMAT: Flow chưa trả về mediaId hợp lệ.');
  return { id: crypto.randomUUID(), mediaId: media.mediaId, name: media.name || 'Ảnh thư viện Flow', url: media.url || '' };
}
export async function readImage(file: File): Promise<Reference> {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) throw new Error('Chọn ảnh PNG, JPG hoặc WebP.');
  if (file.size > 8 * 1024 * 1024) throw new Error('Ảnh tham chiếu tối đa 8 MB.');
  const url = await new Promise<string>((resolve, reject) => { const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result)); reader.onerror = () => reject(new Error('Không đọc được ảnh.')); reader.readAsDataURL(file);
  });
  await new Promise<void>((resolve, reject) => { const img = new Image(); img.onload = () => resolve(); img.onerror = () => reject(new Error('Tệp ảnh bị hỏng hoặc không hỗ trợ.')); img.src = url; });
  return { id: crypto.randomUUID(), name: file.name, url, base64: url.split(',')[1], mimeType: file.type };
}
function videoResult(base64: string, mimeType = 'video/mp4', demo = false): VideoResult {
  if (!base64 || !/^video\/(mp4|webm|quicktime)$/.test(mimeType)) throw new Error('SDK_VIDEO_FORMAT: Cần {base64, mimeType: video/mp4 hoặc video/webm}.');
  const clean = base64.replace(/^data:[^;]+;base64,/, '').replace(/\s/g, '');
  let binary: string;
  try { binary = atob(clean); } catch { throw new Error('SDK_VIDEO_FORMAT: Dữ liệu video base64 không hợp lệ.'); }
  const bytes = Uint8Array.from(binary, c => c.charCodeAt(0));
  return { base64: clean, mimeType, url: URL.createObjectURL(new Blob([bytes], { type: mimeType })), demo };
}
export function releaseVideo(video?: VideoResult) { if (video?.url.startsWith('blob:')) URL.revokeObjectURL(video.url); }
export async function generateVideo(prompt: string, reference: Reference | null, settings: Settings, signal: AbortSignal, accountId: number): Promise<VideoResult> {
  signal.throwIfAborted();
  const fullPrompt = [prompt.trim(), settings.modifier.trim()].filter(Boolean).join('\n\n');
  if (!fullPrompt) throw new Error('Hãy nhập kịch bản cho cảnh trước khi tạo.');
  let result: FlowVideo;
  if (settings.mode === 'flow') {
    const flow = requireFlow();
    if (reference && settings.r2v && !reference.mediaId) throw new Error('SDK_MEDIA_REQUIRED: Chọn ảnh từ thư viện Flow để có mediaId R2V.');
    result = await waitForSDK(flow.generate.video({ prompt: fullPrompt, modelDisplayName: settings.model,
      referenceImageMediaIds: settings.r2v && reference?.mediaId ? [reference.mediaId] : [],
      aspectRatio: settings.aspectRatio, durationSeconds: settings.duration, resolution: settings.resolution }), signal);
  } else if (settings.mode === 'muse') {
    if (reference && settings.r2v && !reference.base64) throw new Error('Tải ảnh từ máy tính để dùng với kết nối Muse AI.');
    result = await api('/api/video', { accountId, prompt: fullPrompt, model: settings.model, aspectRatio: settings.aspectRatio,
      duration: settings.duration, resolution: settings.resolution,
      image: settings.r2v && reference ? { imageBytes: reference.base64, mimeType: reference.mimeType } : undefined }, signal);
  } else {
    // An explicitly labelled transport/UI test, never presented as AI generation.
    await new Promise<void>((resolve, reject) => {
      const finish = () => { signal.removeEventListener('abort', abort); resolve(); };
      const timeout = setTimeout(finish, 550);
      const abort = () => { clearTimeout(timeout); reject(new DOMException('Đã dừng', 'AbortError')); };
      signal.addEventListener('abort', abort, { once: true });
    });
    const response = await fetch('/demo.mp4', { signal });
    if (!response.ok) throw new Error('Không tìm thấy clip kiểm thử đi kèm.');
    const bytes = new Uint8Array(await response.arrayBuffer());
    let binary = '';
    for (const byte of bytes) binary += String.fromCharCode(byte);
    result = { base64: btoa(binary), mimeType: 'video/mp4' };
  }
  signal.throwIfAborted();
  if (!result || typeof result.base64 !== 'string') throw new Error('SDK_VIDEO_FORMAT: Adapter chưa trả về {base64, mimeType}. Xem README để đối chiếu SDK thực tế.');
  return videoResult(result.base64, result.mimeType, settings.mode === 'demo');
}
export async function enhancePrompt(prompt: string, mode: Mode, signal: AbortSignal, accountId: number): Promise<string> {
  if (mode === 'demo') throw new Error('Chế độ kiểm thử không có AI Enhance. Kết nối Flow hoặc Muse AI để trau chuốt thật.');
  const instruction = `Rewrite this scene as one concise cinematic video prompt in English. Preserve the characters, action and narrative. Add specific camera movement, composition and lighting. Return only the rewritten prompt, no headings. Scene:\n${prompt}`;
  const result = mode === 'flow' ? await waitForSDK(requireFlow().generate.text({ prompt: instruction }), signal) : await api('/api/text', { prompt: instruction, accountId }, signal);
  signal.throwIfAborted();
  const text = typeof result === 'string' ? result : result?.text;
  if (typeof text !== 'string' || !text.trim()) throw new Error('AI không trả về prompt văn bản.');
  return text.trim().slice(0, 8000);
}
export async function downloadVideo(video: VideoResult, id: number, mode: Mode) {
  const ext = video.mimeType === 'video/webm' ? 'webm' : video.mimeType === 'video/quicktime' ? 'mov' : 'mp4';
  const filename = `${video.demo ? 'kiem-thu' : 'scene'}-${String(id).padStart(2, '0')}.${ext}`;
  if (mode === 'flow' && !video.demo && window.Flow?.download) {
    await window.Flow.download({ base64: video.base64, mimeType: video.mimeType, filename });
  } else { const a = document.createElement('a'); a.href = video.url; a.download = filename; document.body.appendChild(a); a.click(); a.remove(); }
}
export const providerStatus = () => api('/api/status');
