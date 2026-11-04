export const MUSE_MODELS = ['Omni 1.1 Flash', 'Veo 3.1 - Lite', 'Veo 3.1 - Fast'] as const;
export const VIDEO_RESOLUTIONS = ['360p', '720p', '1080p', '2k', '4k'] as const;
export type Model = typeof MUSE_MODELS[number];
export type Resolution = typeof VIDEO_RESOLUTIONS[number];
export type Mode = 'muse' | 'demo';
export type Output = 'video' | 'image';
export type Status = 'ready' | 'queued' | 'running' | 'done' | 'error' | 'cancelled';
export type Reference = { id: string; name: string; url: string; base64?: string; mimeType?: string };
export type Settings = { model: Model; aspectRatio: '16:9' | '9:16'; duration: number; resolution: Resolution; imageResolution: '2k' | '4k'; output: Output; videoInput: 'text' | 'image'; autoSync: boolean; r2v: boolean; modifier: string; mode: Mode };
export type MediaResult = { kind: Output; base64: string; mimeType: string; url: string; demo: boolean; referenceCompressed?: boolean; metadata?: { duration?: number; width: number; height: number }; requestedResolution?: Resolution; aspectRatio?: Settings['aspectRatio'] };
export type VideoResult = MediaResult;
export type ImageResult = MediaResult;
export type Scene = { id: number; enabled: boolean; prompt: string; reference: Reference | null; status: Status; error?: string; video?: VideoResult; image?: ImageResult; enhancing?: boolean };
export const ADVENTURE = [
  'Một người thám hiểm bước vào ngôi đền cổ xưa trong rừng nhiệt đới, tia nắng vàng rọi xuyên qua tán lá, máy quay tiến chậm từ phía sau.',
  'Khám phá bức tường khắc cổ ngữ bí ẩn phát sáng ánh lân tinh xanh ngọc, máy quay lia chậm ngang qua các chi tiết.',
  'Bầy đá cổ rung chuyển khi người thám hiểm chạm vào viên ngọc đỏ, khói bụi mờ ảo và ánh sáng kịch tính.',
  'Chạy thật nhanh qua cây cầu treo gỗ đung đưa trên vực thẳm thác nước gầm rú, camera tracking góc thấp tốc độ cao.',
  'Nhảy sang bờ đá bên kia an toàn, quay cận biểu cảm hồi hộp căng thẳng toát mồ hôi dưới mưa rừng.',
  'Người thám hiểm giơ ngọn đuốc trong hang pha lê, hàng nghìn tinh thể phản chiếu ánh lửa ấm áp.',
  'Một cánh cửa đá khổng lồ mở ra, ánh sáng tràn vào kho báu thất lạc, góc máy rộng điện ảnh.',
  'Cận cảnh bàn tay phủi bụi trên bản đồ cổ bằng vàng, ánh đuốc chuyển động trên những ký tự.',
  'Người thám hiểm bước ra khỏi hang khi bình minh ló dạng, biển mây trải dài bên dưới vách núi.',
  'Toàn cảnh người thám hiểm đứng trên đỉnh núi nhìn về chân trời, máy quay kéo xa, kết thúc cuộc phiêu lưu.'
];
export const RUNWAY = [
  'Người mẫu bước ra từ hậu trường trong bộ suit đen, ánh đèn sân khấu trắng, toàn cảnh sàn runway.',
  'Cận cảnh gương mặt tự tin và kiểu tóc thanh lịch, camera dolly chậm dưới ánh sáng studio mềm.',
  'Bước đi uyển chuyển trên sàn catwalk phản chiếu, trang phục lụa chuyển động tự nhiên.',
  'Góc quay thấp ghi lại từng bước giày cao gót trên sàn, ánh đèn flash phía khán giả.',
  'Người mẫu dừng lại tạo dáng ở cuối runway, máy quay xoay nhẹ để thấy phom dáng trang phục.',
  'Cận cảnh chất liệu vải và chi tiết đường may, ánh sáng viền tinh tế, hậu cảnh mờ.',
  'Người mẫu xoay người, tà áo tung nhẹ, chuyển động chậm điện ảnh.',
  'Góc máy ngang theo bước chân người mẫu trở về, ánh đèn xanh tím hiện đại.',
  'Người mẫu ngoái nhìn qua vai với nụ cười nhẹ, camera chân dung 85mm.',
  'Người mẫu đứng giữa sân khấu trong ánh đèn cuối buổi, toàn cảnh runway sang trọng.'
];
export const DEFAULT_SETTINGS: Settings = { model: 'Omni 1.1 Flash', aspectRatio: '16:9', duration: 4, resolution: '720p', imageResolution: '2k', output: 'video', videoInput: 'text', autoSync: true, r2v: true, modifier: '', mode: 'muse' };
export const createScenes = (): Scene[] => ADVENTURE.map((prompt, i) => ({ id: i + 1, enabled: true, prompt, reference: null, status: 'ready' }));

// Subtitle blocks become scenes; TXT uses paragraphs, or one non-empty line per scene.
export function parseScript(text: string): string[] {
  const normalized = text.replace(/^\uFEFF/, '').replace(/\r\n?/g, '\n').trim();
  if (!normalized) return [];
  const timestamp = /\d{1,2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{1,2}:\d{2}:\d{2}[,.]\d{3}/;
  if (timestamp.test(normalized)) {
    const scenes: string[] = [];
    let current: string[] = [];
    const flush = () => { if (current.length) scenes.push(current.join(' ').replace(/<[^>]*>/g, '').trim()); current = []; };
    for (const line of normalized.split('\n')) {
      if (timestamp.test(line)) { flush(); continue; }
      if (!line.trim()) { flush(); continue; }
      if (/^\d+$/.test(line.trim())) continue;
      current.push(line.trim());
    }
    flush();
    return scenes.filter(Boolean);
  }
  const paragraphs = normalized.split(/\n\s*\n/);
  return (paragraphs.length > 1 ? paragraphs : normalized.split('\n'))
    .map(s => s.replace(/^\s*(?:#?\d+[.)\-:]|[-•])\s+/, '').trim()).filter(Boolean);
}
export function normalizeSettings(settings: Settings): Settings {
  return settings.model === 'Omni 1.1 Flash' ? settings : { ...settings, duration: 8 };
}
export function requestedDimensions(resolution: Resolution, ratio: Settings['aspectRatio']): { width: number; height: number } {
  const [width, height] = ({ '360p': [640, 360], '720p': [1280, 720], '1080p': [1920, 1080], '2k': [2560, 1440], '4k': [3840, 2160] } as const)[resolution];
  return ratio === '9:16' ? { width: height, height: width } : { width, height };
}
export function meetsResolution(media: MediaResult): boolean | null {
  if (media.demo || !media.metadata || !media.requestedResolution || !media.aspectRatio) return null;
  const target = requestedDimensions(media.requestedResolution, media.aspectRatio);
  return media.metadata.width >= target.width && media.metadata.height >= target.height && Math.abs(media.metadata.width / media.metadata.height - target.width / target.height) < 0.03;
}
export function errorInfo(error: unknown): { raw: string; hint: string } {
  const raw = error instanceof Error ? error.message : String(error);
  let hint = 'Thử lại sau hoặc mở Chẩn đoán API để kiểm tra kết nối.';
  if (/MUSE_LOGIN_REQUIRED/i.test(raw)) hint = 'Mở Tài khoản Muse, đăng nhập trong tool rồi bấm Kiểm tra phiên. Cả 10 luồng sử dụng chung tài khoản.';
  else if (/MUSE_SESSION_REFRESH_FAILED|MUSE_SESSION_CHECK_FAILED/i.test(raw)) hint = 'Chưa cập nhật được phiên Muse. Kiểm tra kết nối và tab Muse rồi bấm Kiểm tra phiên; thông tin đăng nhập vẫn được giữ trên máy.';
  else if (/MUSE_WORKSPACE_ORIGIN/i.test(raw)) hint = 'Trang luồng chuyển sang miền khác Muse. Hoàn tất đăng nhập trong tab Muse rồi kiểm tra lại phiên; chưa có prompt được gửi.';
  else if (/MUSE_COMPOSER_NOT_READY/i.test(raw)) hint = 'Chưa tìm được ô nhập Message cho cảnh này. Bấm Kiểm tra ô Message ở bảng tài khoản để xem chi tiết trang luồng; chưa có prompt được gửi.';
  else if (/MUSE_COMPOSER_AMBIGUOUS/i.test(raw)) hint = 'Có nhiều ô nhập Message phù hợp cho cảnh này. Tool chưa gửi prompt để tránh chọn nhầm ô.';
  else if (/MUSE_BROWSER_UNAVAILABLE|MUSE_PROFILE_BUSY/i.test(raw)) hint = 'Kiểm tra Chrome/Edge trên máy chạy tool và cửa sổ hồ sơ Muse đang mở. Thông tin chi tiết ở mã lỗi gốc.';
  else if (/credit|quota|resource_exhausted|429|billing/i.test(raw)) hint = 'Kiểm tra hạn mức hoặc thanh toán trong tài khoản nhà cung cấp.';
  else if (/safety|filter|blocked|policy|rai|responsible/i.test(raw)) hint = 'Nội dung hoặc ảnh có thể bị bộ lọc từ chối. Chỉnh kịch bản, dùng ảnh phù hợp rồi thử lại.';
  else if (/overload|unavailable|503|502|gpu/i.test(raw)) hint = 'Dịch vụ đang bận hoặc tạm ngừng. Đợi một lúc rồi tạo lại cảnh lỗi.';
  else if (/401|403|key|permission|auth/i.test(raw)) hint = 'Kiểm tra quyền truy cập, API key và mô hình được cấp cho tài khoản.';
  else if (/MUSE_NOT_CONFIGURED/i.test(raw)) hint = 'Chưa kết nối dịch vụ Muse AI. Cần cấu hình API hoặc adapter chính thức của dịch vụ Muse bạn đang dùng.';
  else if (/MODEL_UNSUPPORTED/i.test(raw)) hint = 'Mô hình chưa được tài khoản Muse hỗ trợ. Kiểm tra quyền truy cập với nhà cung cấp.';
  else if (/abort|cancel/i.test(raw)) hint = 'Đã dừng nhận kết quả. Nhà cung cấp vẫn có thể tính phí cho yêu cầu đã gửi.';
  return { raw: raw.slice(0, 4000), hint };
}
export function restoreWorkspace(raw: string | null): { scenes: Scene[]; settings: Settings } {
  const fallback = { scenes: createScenes(), settings: { ...DEFAULT_SETTINGS } };
  if (!raw) return fallback;
  try {
    const data = JSON.parse(raw);
    if (data.version !== 1 || !Array.isArray(data.scenes) || data.scenes.length !== 10) return fallback;
    fallback.scenes = fallback.scenes.map((scene, i) => ({ ...scene,
      prompt: typeof data.scenes[i]?.prompt === 'string' ? data.scenes[i].prompt.slice(0, 8000) : scene.prompt,
      enabled: data.scenes[i]?.enabled !== false
    }));
    const s = data.settings ?? {};
    fallback.settings = normalizeSettings({ ...DEFAULT_SETTINGS,
      model: MUSE_MODELS.includes(s.model) ? s.model : DEFAULT_SETTINGS.model,
      aspectRatio: s.aspectRatio === '9:16' ? '9:16' : '16:9',
      duration: [4, 6, 8, 10].includes(s.duration) ? s.duration : 4,
      resolution: VIDEO_RESOLUTIONS.includes(s.resolution) ? s.resolution : '720p',
      imageResolution: s.imageResolution === '4k' ? '4k' : '2k', output: s.output === 'image' ? 'image' : 'video',
      videoInput: s.videoInput === 'image' ? 'image' : 'text', autoSync: s.autoSync !== false, r2v: s.r2v !== false,
      modifier: typeof s.modifier === 'string' ? s.modifier.slice(0, 2000) : '', mode: s.mode === 'demo' ? 'demo' : 'muse'
    });
    return fallback;
  } catch { return fallback; }
}
