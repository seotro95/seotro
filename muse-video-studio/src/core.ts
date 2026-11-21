import {MAX_SLOTS,MAX_ACCOUNTS,MAX_ACCOUNT_LANES,DEFAULT_SLOTS,isSlotCount,isAccountId,isLaneCount} from '../limits.mjs';
export const MUSE_MODELS = ['Omni 1.1 Flash', 'Veo 3.1 - Lite', 'Veo 3.1 - Fast'] as const;
export const VIDEO_RESOLUTIONS = ['360p', '720p', '1080p', '2k', '4k'] as const;
export type Model = typeof MUSE_MODELS[number];
export type Resolution = typeof VIDEO_RESOLUTIONS[number];
export type Mode = 'muse' | 'demo';
export type Output = 'video' | 'image';
export type Status = 'ready' | 'queued' | 'running' | 'done' | 'error' | 'cancelled';
export type Reference = { id: string; name: string; url: string; base64?: string; mimeType?: string };
export type Settings = { accountPlanMode?:'standard'|'expanded'; standardAccountIds?:number[]; expandedPlan?:{accountIds:number[];lanes:number;overrides?:Record<string,number>}; accountLaneOverrides?: Record<string,number>; selectedAccountIds?: number[]; slotCount: number; singleAccountId?: number; multipleSlotIds?: number[]; requestedConcurrency?: number; syncOperations: boolean; accountMode: 'single' | 'multiple'; model: Model; aspectRatio: '16:9' | '9:16'; duration: number; resolution: Resolution; imageResolution: '2k' | '4k'; output: Output; videoInput: 'text' | 'image'; autoSync: boolean; r2v: boolean; modifier: string; mode: Mode };
export const RENDER_KEYS = ['model','aspectRatio','duration','resolution','imageResolution','videoInput','r2v','modifier'] as const;
export type SceneSettings = Pick<Settings,typeof RENDER_KEYS[number]>;
export function renderingSettings(settings:Settings):SceneSettings{return Object.fromEntries(RENDER_KEYS.map(key=>[key,settings[key]])) as SceneSettings}
export function sceneSettings(settings:Settings,scene:Pick<Scene,'renderSettings'>):Settings{return normalizeSettings({...settings,...scene.renderSettings})}
export type MediaResult = { outputName?: string; kind: Output; base64: string; mimeType: string; url: string; demo: boolean; savedId?: string; referenceCompressed?: boolean; metadata?: { duration?: number; width: number; height: number }; requestedResolution?: Resolution; aspectRatio?: Settings['aspectRatio'] };
export type VideoResult = MediaResult;
export type ImageResult = MediaResult;
export type Scene = { outputName?: string; id: number; accountId?: number; enabled: boolean; syncSelected?: boolean; renderSettings?: SceneSettings; prompt: string; reference: Reference | null; status: Status; error?: string; video?: VideoResult; image?: ImageResult; enhancing?: boolean; stopping?: boolean; activeOutput?: Output };
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
export const DEFAULT_SETTINGS: Settings = { slotCount: DEFAULT_SLOTS, requestedConcurrency:1, accountPlanMode:'expanded', syncOperations:true, accountMode: 'single', model: 'Omni 1.1 Flash', aspectRatio: '16:9', duration: 4, resolution: '720p', imageResolution: '2k', output: 'video', videoInput: 'text', autoSync: true, r2v: true, modifier: '', mode: 'muse' };
export const createScenes = (count: number = DEFAULT_SLOTS): Scene[] => Array.from({length:isSlotCount(count)?count:DEFAULT_SLOTS},(_,i)=>({id:i+1,enabled:true,prompt:ADVENTURE[i]||'',reference:null,status:'ready'}));

export { parseScriptEntries, extractScriptEntry } from './script-import.ts';
import { parseScriptEntries } from './script-import.ts';
import { outputStem } from '../output-names.mjs';
export function parseScript(text:string):string[]{return parseScriptEntries(text).map(entry=>entry.prompt)}
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
  if (/MUSE_WAIT_LIMIT|MUSE_TIMEOUT/i.test(raw)) hint = 'Đã chạm giới hạn chờ tối đa 250 giây. Kiểm tra phản hồi và kết quả trong Muse; yêu cầu đã gửi không được tự tạo lại.';
  else if (/MUSE_BATCH_UNMATCHED/i.test(raw)) hint = 'Muse đã trả media nhưng tool chưa ghép được tệp với đúng ô. Bấm Nhận lại từ Muse để chỉ lấy kết quả đã tạo; chưa cần gửi lại prompt.';
  else if (/MUSE_RECOVER_HISTORY_MISSING/i.test(raw)) hint = 'Mở đúng cuộc trò chuyện trong Đăng nhập Muse trong tool và mở rộng tin nhắn prompt rồi bấm Nhận lại. Tool chưa gửi lệnh tạo mới.';
  else if (/MUSE_RECOVER_/i.test(raw)) hint = 'Chưa lấy lại được tệp đúng với số ô và prompt. Xem chi tiết bên dưới; thao tác này không tạo video hoặc ảnh mới.';
  else if (/MUSE_LOCAL_CONNECTION|MUSE_LOCAL_TIMEOUT|MUSE_LOCAL_RESPONSE/i.test(raw)) hint = 'Kết nối giữa giao diện và máy chủ trong tool bị lỗi. Giữ tool mở và dùng Sao chép lỗi để xem mã kết nối; kiểm tra lịch sử Muse trước khi tạo lại.';
  else if (/MUSE_MEDIA_UNREADABLE/i.test(raw)) hint = 'Tool chưa tải hoặc giải mã được tệp trả về. Xem chi tiết lỗi gốc và lịch sử Muse; không cần tạo lại nếu media đã hoàn thành ở Muse.';
  else if (/MUSE_ACTION_REQUIRED/i.test(raw)) hint = 'Muse đang yêu cầu xác nhận thay vì tạo nội dung. Xem câu trả lời Muse trong mã lỗi; tool không tự xác nhận hoặc gửi lại yêu cầu đã nhận.';
  else if (/MUSE_GENERATION_REFUSED/i.test(raw)) hint = 'Muse đã trả lời rằng chưa thể tạo nội dung theo yêu cầu. Xem lý do gốc về mô hình, quyền hoặc số dư, rồi điều chỉnh trước khi tạo lại.';
  else if (/MUSE_PROMPT_CLARIFICATION/i.test(raw)) hint = 'Muse yêu cầu làm rõ prompt. Viết mô tả ảnh/video cụ thể rồi tạo lại ô này.';
  else if (/MUSE_LOGIN_REQUIRED/i.test(raw)) hint = 'Mở Tài khoản Muse, đăng nhập trong tool rồi bấm Kiểm tra phiên. Mỗi cảnh dùng tài khoản được ghi trên ô.';
  else if (/MUSE_SESSION_REFRESH_FAILED|MUSE_SESSION_CHECK_FAILED/i.test(raw)) hint = 'Chưa cập nhật được phiên Muse. Kiểm tra kết nối và tab Muse rồi bấm Kiểm tra phiên; thông tin đăng nhập vẫn được giữ trên máy.';
  else if (/MUSE_PARALLEL_UNVERIFIED/i.test(raw)) hint = 'Chưa mở được các hội thoại riêng. Tool tự chuyển tài khoản đó sang từng luồng một và giữ đủ các ô chờ.';
  else if (/MUSE_WORKSPACE_ORIGIN/i.test(raw)) hint = 'Trang luồng chuyển sang miền khác Muse. Hoàn tất đăng nhập trong tab Muse rồi kiểm tra lại phiên; chưa có prompt được gửi.';
  else if (/MUSE_SUBMIT_NOT_ACKNOWLEDGED/i.test(raw)) hint = 'Muse chưa xác nhận đã nhận prompt. Mở cuộc trò chuyện kiểm tra trước khi thử lại để tránh tạo trùng; tool không tự gửi lại.';
  else if (/MUSE_NEW_CHAT_UNAVAILABLE/i.test(raw)) hint = 'Tool chưa mở được hội thoại riêng. Dùng chế độ hàng đợi một cảnh mỗi lượt; lỗi này không xác nhận Muse đang bận hoặc hết hạn mức.';
  else if (/MUSE_SHARED_CONVERSATION/i.test(raw)) hint = 'Hội thoại Muse nhận các yêu cầu xen kẽ. Tool dừng để tránh ghép nhầm ảnh; hãy chạy lại từng cảnh sau khi kiểm tra lịch sử.';
  else if (/MUSE_DUPLICATE_MEDIA/i.test(raw)) hint = 'Ảnh nhận được trùng hoàn toàn với một cảnh khác. Tool chưa tính là ảnh mới; kiểm tra kết quả và lịch sử Muse trước khi tạo lại.';
  else if (/MUSE_DRAFT_CHANGED|MUSE_EDITOR_CHANGED/i.test(raw)) hint = 'Ô Message thay đổi khi đang nhập. Tool dừng trước khi gửi; kiểm tra bản nháp trong cuộc trò chuyện.';
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
    if (data.version !== 1 || !Array.isArray(data.scenes) || !isSlotCount(data.scenes.length)) return fallback;
    fallback.scenes = createScenes(data.scenes.length).map((scene, i) => ({ ...scene,
      outputName:outputStem(data.scenes[i]?.outputName)||undefined,
      prompt: typeof data.scenes[i]?.prompt === 'string' ? data.scenes[i].prompt.slice(0, 8000) : scene.prompt,
      enabled: data.scenes[i]?.enabled !== false, syncSelected:data.scenes[i]?.syncSelected!==false,
      accountId:validAccountId(data.scenes[i]?.accountId) ?? (data.settings?.selectedAccountIds===undefined&&scene.id<=MAX_ACCOUNTS?scene.id:undefined),
      renderSettings:validSceneSettings(data.scenes[i]?.renderSettings)
    }));
    const s = data.settings ?? {};
    fallback.settings = normalizeSettings({ ...DEFAULT_SETTINGS,
      slotCount: isSlotCount(s.slotCount)?s.slotCount:data.scenes.length, requestedConcurrency:isLaneCount(s.requestedConcurrency)?s.requestedConcurrency:(isSlotCount(s.requestedConcurrency)?MAX_ACCOUNT_LANES:DEFAULT_SETTINGS.requestedConcurrency),syncOperations:s.syncOperations!==false,
      singleAccountId:validAccountId(s.singleAccountId) ?? 1,
      multipleSlotIds:normalizeSlotIds(s.multipleSlotIds), selectedAccountIds:normalizeAccountIds(s.selectedAccountIds), accountLaneOverrides:normalizeLaneOverrides(s.accountLaneOverrides),
      accountMode: s.accountMode === 'multiple' ? 'multiple' : 'single',
      accountPlanMode:s.accountPlanMode==='standard'?'standard':s.accountPlanMode==='expanded'||s.accountMode!=='multiple'||Number(s.requestedConcurrency)>1||Object.values(normalizeLaneOverrides(s.accountLaneOverrides)||{}).some(value=>value>1)?'expanded':'standard',
      standardAccountIds:normalizeAccountIds(s.standardAccountIds),
      expandedPlan:s.expandedPlan&&normalizeAccountIds(s.expandedPlan.accountIds)?.length&&isLaneCount(s.expandedPlan.lanes)?{accountIds:normalizeAccountIds(s.expandedPlan.accountIds)!,lanes:s.expandedPlan.lanes,overrides:normalizeLaneOverrides(s.expandedPlan.overrides)}:undefined,
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
function validSceneSettings(value:unknown):SceneSettings|undefined{
  if(!value||typeof value!=='object')return undefined;const s=value as SceneSettings;
  return renderingSettings(normalizeSettings({...DEFAULT_SETTINGS,model:MUSE_MODELS.includes(s.model)?s.model:DEFAULT_SETTINGS.model,aspectRatio:s.aspectRatio==='9:16'?'9:16':'16:9',duration:[4,6,8,10].includes(s.duration)?s.duration:4,resolution:VIDEO_RESOLUTIONS.includes(s.resolution)?s.resolution:'720p',imageResolution:s.imageResolution==='4k'?'4k':'2k',videoInput:s.videoInput==='image'?'image':'text',r2v:s.r2v!==false,modifier:typeof s.modifier==='string'?s.modifier.slice(0,2000):''}));
}

export function validAccountId(id:unknown):number|undefined{return isAccountId(id)?Number(id):undefined}
export function accountForScene(scene:Pick<Scene,'id'|'accountId'>,settings:Settings):number{
 if(settings.accountMode!=='multiple')return validAccountId(settings.singleAccountId)??1;
 const explicit=validAccountId(scene.accountId);if(explicit)return explicit;
 const ids=accountPool(settings);let offset=(scene.id-1)%ids.reduce((sum,id)=>sum+lanesForAccount(settings,id),0);
 for(const id of ids){const count=lanesForAccount(settings,id);if(offset<count)return id;offset-=count}
 return ids[0];
}

export function normalizeSlotIds(value:unknown):number[]|undefined{
  if(!Array.isArray(value))return undefined;
  return [...new Set(value.filter(id=>isSlotCount(id)) as number[])].sort((a,b)=>a-b);
}
export function visibleSlotIds(settings:Settings):number[]{
  return settings.accountMode==='multiple'&&settings.multipleSlotIds!==undefined
    ? normalizeSlotIds(settings.multipleSlotIds)??[]
    : Array.from({length:settings.slotCount},(_,i)=>i+1);
}
export function visibleWorkspace(scenes:Scene[],settings:Settings):Scene[]{
  const ids=new Set(visibleSlotIds(settings));return scenes.filter(scene=>ids.has(scene.id));
}

export function normalizeAccountIds(value:unknown):number[]|undefined{
 if(!Array.isArray(value))return undefined;
 return [...new Set(value.filter(id=>isAccountId(id)) as number[])].sort((a,b)=>a-b);
}
export function accountPool(settings:Settings):number[]{return settings.accountMode==='single'?[validAccountId(settings.singleAccountId)??1]:(normalizeAccountIds(settings.selectedAccountIds)?.length?normalizeAccountIds(settings.selectedAccountIds)!:Array.from({length:10},(_,i)=>i+1))}
export function accountLayout(ids:number[],lanes:number,overrides?:Record<string,number>):{id:number;accountId:number}[]{
 if(!ids.length||ids.length>MAX_ACCOUNTS||new Set(ids).size!==ids.length||ids.some(id=>!isAccountId(id))||!isLaneCount(lanes))throw new Error('Chọn 1–40 tài khoản và 1–10 ô mỗi tài khoản.');
 let next=1;return ids.flatMap(accountId=>Array.from({length:isLaneCount(overrides?.[accountId])?overrides![accountId]:lanes},()=>({id:next++,accountId})));
}

export function normalizeLaneOverrides(value:unknown):Record<string,number>|undefined{
 if(!value||typeof value!=='object'||Array.isArray(value))return undefined;
 return Object.fromEntries(Object.entries(value).filter(([id,count])=>/^[1-9]\d*$/.test(id)&&isAccountId(Number(id))&&isLaneCount(count)));
}
export function lanesForAccount(settings:Settings,id:number):number{
 if(settings.accountPlanMode==='standard')return 1;
 const override=settings.accountMode==='multiple'?settings.accountLaneOverrides?.[id]:undefined;
 return isLaneCount(override)?override!:isLaneCount(settings.requestedConcurrency)?settings.requestedConcurrency!:1;
}
