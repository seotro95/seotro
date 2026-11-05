import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Play, Download, FileText, Users, ShieldPlus, ImagePlus, ScanFace, WandSparkles, Clapperboard, X, Check, ChevronDown, RefreshCw, Square, Settings2, Activity, ArrowRight, Copy, Upload, FolderOpen, CircleAlert, Video, Link2, Trash2, Film, FlaskConical, CheckCheck, LoaderCircle } from 'lucide-react';
import { ADVENTURE, RUNWAY, MUSE_MODELS, normalizeSettings, restoreWorkspace, parseScript, errorInfo, meetsResolution } from './core.ts';
import type { Scene, Settings, Reference, Status, Mode, Output, MediaResult } from './core.ts';
import { generateVideo, generateImage, enhancePrompt, readImage, downloadVideo, downloadMediaBatch, chooseExportDirectory, releaseVideo, providerStatus, accountAction } from './provider.ts';
import { loadMedia, saveMedia, deleteMedia } from './media-library.ts';
import type { SavedMedia } from './media-library.ts';
import './styles.css';

const STORAGE = 'muse-workstation-v1';
const statusNames: Record<Status, string> = { ready: 'Sẵn sàng', queued: 'Đang chờ', running: 'Đang tạo', done: 'Hoàn tất', error: 'Lỗi', cancelled: 'Đã dừng' };
type Log = { time: string; scene: string; raw: string; hint: string };
type ModalName = 'import' | 'accounts' | 'diagnostics' | null;
type Balance = { valueText: string; unit: 'token' | 'credit'; label: string; observedAt: string; source: string };
type AccountSession = { label?: string; running?: number; balance?: Balance | null; id: number; state: string; authenticated: boolean; sessionAuthenticated?: boolean; composerReady?: boolean; connectionMessage?: string; checkedAt: string | null; active: boolean };
type ProviderStatus = { multiAccount?: boolean; museConfigured: boolean; busy: boolean; transport?: 'browser' | 'adapter'; accounts?: AccountSession[]; embeddedLogin?: boolean; activeRequests?: number; maxConcurrency?: number; executionConcurrency?: number; workerProgress?: { batchId: string | null; sceneId: number | null; output: string; phase: string; submitted: boolean; active: boolean }[] };
type RenderJob = { accountId: number; scene: Scene; settings: Settings; action: 'render' | 'enhance'; control: AbortController; started: boolean };
type RenderBatch = { control: AbortController; batchId: string; completed: number; failed: number; cancelled: number; loginRequired: boolean };
const hasVerifiedSession = (account?: AccountSession) => Boolean(account?.sessionAuthenticated ?? account?.authenticated);
const accountStateName = (account?: AccountSession) => !account ? 'Chưa kết nối' : hasVerifiedSession(account) ? account.active ? 'Đã xác minh' : 'Phiên đã lưu' : account.state === 'awaiting_code' ? 'Đang chờ mã xác nhận' : account.state === 'check_failed' ? 'Chưa xác minh được phiên' : account.state === 'login_open' ? 'Chờ đăng nhập' : account.state === 'saved' || account.state === 'session_saved' ? 'Cần kiểm tra phiên' : 'Chưa kết nối';
function load() { try { return restoreWorkspace(localStorage.getItem(STORAGE)); } catch { return restoreWorkspace(null); } }
const initial = load();
function referenceKey(scene: Scene, config: Settings) {
  return config.r2v || (config.output === 'video' && config.videoInput === 'image') ? scene.reference?.id || (config.output === 'video' && config.videoInput === 'image' ? scene.image?.savedId : undefined) : undefined;
}
function matchesRequest(entry: SavedMedia | undefined, scene: Scene, config: Settings) {
  const previous = entry?.settings;
  if (!entry || !previous || entry.prompt !== scene.prompt || entry.referenceId !== referenceKey(scene, config)) return false;
  const keys: (keyof Settings)[] = ['mode', 'output', 'modifier', 'aspectRatio', 'r2v', ...(config.output === 'image' ? ['imageResolution'] as const : ['resolution', 'model', 'duration', 'videoInput'] as const)];
  return keys.every(key => previous[key] === config[key]);
}

function Modal({ title, eyebrow, children, close, wide = false }: { title: string; eyebrow: string; children: React.ReactNode; close: () => void; wide?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { const dialog = ref.current!; const previous = document.activeElement as HTMLElement;
    dialog.showModal(); return () => { dialog.close(); previous?.focus(); };
  }, []);
  return <dialog ref={ref} className={`modal${wide ? ' wide-modal' : ''}`} onCancel={e => { e.preventDefault(); close(); }} onClick={e => { if (e.target === e.currentTarget) close(); }} aria-labelledby="modal-title">
    <header className="modal-head"><div><span className="eyebrow">{eyebrow}</span><h2 id="modal-title">{title}</h2></div><button className="icon-button" aria-label="Đóng" onClick={close}><X size={19}/></button></header>
    {children}
  </dialog>;
}

function App() {
  const [scenes, setScenes] = useState(initial.scenes);
  const scenesRef = useRef(scenes);
  const [settings, setSettings] = useState(initial.settings);
  const settingsRef = useRef(settings);
  const museLanes = useRef(1);
  const [globalImage, setGlobalImage] = useState<Reference | null>(null);
  const [library, setLibrary] = useState<SavedMedia[]>([]);
  const libraryRef = useRef(library);
  const [libraryLoading, setLibraryLoading] = useState(true);
  const [deletingMedia, setDeletingMedia] = useState<string | null>(null);
  const [modal, setModal] = useState<ModalName>(null);
  const [viewer, setViewer] = useState<{ id: number; media: MediaResult } | null>(null);
  const [viewerNatural, setViewerNatural] = useState(false);
  const [busy, setBusy] = useState(false);
  const [batch, setBatch] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [imageBusy, setImageBusy] = useState(false);
  const [logs, setLogs] = useState<Log[]>([]);
  const [notice, setNotice] = useState('');
  const [importText, setImportText] = useState('');
  const [status, setStatus] = useState<ProviderStatus | null>(null);
  const [connectingId, setConnectingId] = useState<number | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [statusError, setStatusError] = useState('');
  const [connectionError, setConnectionError] = useState('');
  const [selectedAccount, setSelectedAccount] = useState(1);
  const [accountList, setAccountList] = useState('');
  const [composerCheck, setComposerCheck] = useState<{ message: string; error?: string; details?: unknown } | null>(null);
  const [diagnosticBusy, setDiagnosticBusy] = useState(false);
  const [diagnostic, setDiagnostic] = useState<{ message: string; error?: string } | null>(null);
  const [diagnosticConsent, setDiagnosticConsent] = useState(false);
  const controller = useRef<AbortController | null>(null);
  const renderJobs = useRef(new Map<number, RenderJob>());
  const renderBatch = useRef<RenderBatch | null>(null);
  const statusPending = useRef(false);
  const imageInput = useRef<HTMLInputElement>(null);
  const imageTarget = useRef<number | 'global'>('global');
  const fileInput = useRef<HTMLInputElement>(null);
  const locked = diagnosticBusy || imageBusy || connectingId !== null || libraryLoading || deletingMedia !== null;
  const renderLocked = locked || (busy && !renderBatch.current) || cancelling;
  const connectionLocked = locked || [...renderJobs.current.values()].some(job => job.settings.mode === 'muse');
  const done = scenes.filter(s => s[settings.output]).length;
  const outputLabel = settings.output === 'image' ? 'ảnh' : 'video';
  const enabled = scenes.filter(s => s.enabled).length;
  const parsed = parseScript(importText);
  const canImport = parsed.length > 0 && parsed.length <= 10;
  const usingBrowser = status?.transport === 'browser';
  const embeddedLogin = Boolean(status?.embeddedLogin);
  const loginPlace = embeddedLogin ? 'tab Muse ngay trong tool' : 'cửa sổ Chrome/Edge của chế độ web';
  const runningCount = scenes.filter(scene => scene.status === 'running').length;
  const multipleAccounts = settings.accountMode === 'multiple';
  const accountFor = (id: number) => multipleAccounts ? id : 1;
  const executionLanes = multipleAccounts ? 10 : settings.mode === 'demo' || !usingBrowser ? 10 : Math.max(1, Math.min(10, status?.executionConcurrency || 1));
  museLanes.current = !usingBrowser ? 10 : Math.max(1, Math.min(10, status?.executionConcurrency || 1));
  const actualProgress = status?.workerProgress?.filter(stage => stage.batchId === renderBatch.current?.batchId) || [];
  const museAccount = status?.accounts?.find(account => account.id === selectedAccount);
  const primaryAccount = status?.accounts?.find(account => account.id === 1);
  const balanceAccount = museAccount;
  const sessionVerified = hasVerifiedSession(museAccount);
  const providerReady = settings.mode === 'demo' || Boolean(status?.museConfigured && (!usingBrowser ? !multipleAccounts : multipleAccounts ? status?.multiAccount && status.accounts?.some(hasVerifiedSession) : hasVerifiedSession(primaryAccount)));
  const accountReady = (scene: Scene) => providerReady && (settings.mode === 'demo' || !usingBrowser || hasVerifiedSession(status?.accounts?.find(account=>account.id===accountFor(scene.id))));
  const sourceReady = (scene: Scene) => settings.output !== 'video' || settings.videoInput !== 'image' || Boolean(scene.reference || scene.image);
  const renderBlocked = !providerReady;
  const connectionProblem = statusLoading ? 'Đang đọc cấu hình kết nối từ máy chủ…' : statusError ? 'Không đọc được cấu hình máy chủ. Kiểm tra cửa sổ chạy tool rồi bấm Đọc cấu hình.' : usingBrowser ? (multipleAccounts ? 'Đăng nhập các tài khoản Muse 01–10. Mỗi ô chỉ chạy trên tài khoản cùng số; ô chưa đăng nhập sẽ được bỏ qua.' : primaryAccount?.connectionMessage) || `Đăng nhập một tài khoản Muse trong ${loginPlace} rồi Kiểm tra phiên. Cả 10 cảnh sử dụng duy nhất phiên này.` : 'Chưa cấu hình adapter Muse riêng. Chọn kết nối trình duyệt trong cấu hình máy chủ để đăng nhập bằng Chrome/Edge.';

  async function refreshStatus(showLoading = true) {
    if (statusPending.current) return;
    statusPending.current = true;
    if (showLoading) setStatusLoading(true);
    setStatusError('');
    try { const result = await providerStatus(); setStatus(result); if (result.accounts?.some(hasVerifiedSession)) setConnectionError(''); }
    catch (e) { setStatus(null); setStatusError(errorInfo(e).raw); }
    finally { setStatusLoading(false); statusPending.current = false; }
  }
  function requireProvider() {
    if (providerReady) return true;
    setModal(usingBrowser ? 'accounts' : 'diagnostics'); setNotice(connectionProblem); return false;
  }
  async function selectAccount(id: number) {
    if(connectionLocked)return;
    setSelectedAccount(id);setConnectingId(id);
    try {await accountAction('select',{accountId:id})}catch(error){setNotice(logError(error,'Chọn tài khoản').raw)}finally{setConnectingId(null)}
  }
  async function connectAccount(check = false, id = selectedAccount) {
    if (connectionLocked) return;
    setSelectedAccount(id); setConnectingId(id);
    setConnectionError('');
    if (!check) setComposerCheck(null);
    try {
      const result = await accountAction(check ? 'check' : 'connect', {accountId:id});
      setStatus(current => current ? { ...current, accounts: result.accounts } : current);
      const account = result.accounts.find((account: AccountSession) => account.id === id);
      setNotice(account?.connectionMessage || (hasVerifiedSession(account) ? 'Đã xác minh phiên tài khoản Muse đang chọn.' : `Đăng nhập trực tiếp trên trang Muse trong ${loginPlace}, rồi quay về Studio bấm Kiểm tra phiên.`));
    } catch (e) { const info = logError(e, 'Kết nối Muse'); setConnectionError(info.raw); setNotice(info.raw); }
    finally { setConnectingId(null); void refreshStatus(false); }
  }

  async function checkAllAccounts() {
    if(connectionLocked)return;
    setConnectingId(selectedAccount);let failures=0;
    try {for(let id=1;id<=10;id++){try{const result=await accountAction('check',{accountId:id});setStatus(current=>current?{...current,accounts:result.accounts}:current)}catch{failures++}}setNotice(`Đã kiểm tra 10 phiên; ${failures} phiên không đọc được. Xem trạng thái từng tài khoản trong danh sách.`)}finally{setConnectingId(null)}
  }

  async function importAccounts() {
    if(connectionLocked)return;
    setConnectingId(selectedAccount);
    try { const result=await accountAction('import',{labels:accountList.replace(/^\uFEFF/,'').split(/\r?\n/).map(value=>value.trim()).filter(Boolean)});setStatus(current=>current?{...current,accounts:result.accounts}:current);setNotice('Đã lưu nhãn tài khoản. Đăng nhập từng phiên Muse để xác thực.'); }
    catch(error){setNotice(logError(error,'Nhập tài khoản').raw)}finally{setConnectingId(null)}
  }

  async function checkComposer() {
    if (connectionLocked || !usingBrowser || !sessionVerified) return;
    setConnectingId(selectedAccount);
    setComposerCheck({ message: 'Đang mở trang luồng để tìm ô Message. Chưa gửi prompt…' });
    try {
      const result = await accountAction('composer',{accountId:selectedAccount});
      setStatus(current => current ? { ...current, accounts: result.accounts } : current);
      setComposerCheck(result.composer);
    } catch (e) { const info = logError(e, 'Kiểm tra ô Message'); setComposerCheck({ message: info.hint, error: info.raw }); }
    finally { setConnectingId(null); void refreshStatus(false); }
  }

  async function changeConcurrency(count: number) {
    if (connectionLocked || !usingBrowser || !hasVerifiedSession(primaryAccount)) return;
    setConnectingId(1);
    setComposerCheck({ message: count === 1 ? 'Đang chuyển sang xử lý lần lượt…' : `Đang kiểm tra ${count} hội thoại riêng. Chưa gửi prompt tạo nội dung…` });
    try {
      const result = await accountAction('concurrency', { concurrency: count, accountId:1 });
      setStatus(current => current ? { ...current, executionConcurrency: result.executionConcurrency } : current);
      setComposerCheck({ message: result.message });
    } catch (e) {
      const info = logError(e, 'Kiểm tra luồng song song');
      setStatus(current => current ? { ...current, executionConcurrency: 1 } : current);
      setComposerCheck({ message: info.hint, error: info.raw });
    } finally { setConnectingId(null); void refreshStatus(false); }
  }

  function updateScenes(fn: (current: Scene[]) => Scene[]) {
    const next = fn(scenesRef.current).map(scene => {
      const job = renderJobs.current.get(scene.id);
      return job ? { ...scene, status: (job.started ? 'running' : 'queued') as Status, activeOutput: job.settings.output, enhancing: job.action === 'enhance' && job.started } : scene;
    });
    scenesRef.current = next; setScenes(next);
  }
  function commitSettings(next: Settings) { settingsRef.current = next; setSettings(next); }
  function updateLibrary(fn: (current: SavedMedia[]) => SavedMedia[]) { const next = fn(libraryRef.current); libraryRef.current = next; setLibrary(next); }
  function selectResult(entry: SavedMedia) {
    if (deletingMedia !== null) return;
    changeScene(entry.sceneId, { [entry.media.kind]: entry.media, status: 'done', error: undefined }, false);
  }
  async function removeResult(entry: SavedMedia) {
    if (downloading || deletingMedia !== null) return;
    setDeletingMedia(entry.id);
    try {
      if (entry.persisted) await deleteMedia(entry.id);
      const remaining = libraryRef.current.filter(item => item.id !== entry.id);
      updateLibrary(() => remaining);
      const kind = entry.media.kind;
      updateScenes(all => all.map(scene => {
        if (scene.id !== entry.sceneId || scene[kind]?.savedId !== entry.id) return scene;
        const media = remaining.find(item => item.sceneId === scene.id && item.media.kind === kind)?.media;
        return { ...scene, [kind]: media, status: settings.output === kind ? media ? 'done' : 'ready' : scene.status };
      }));
      URL.revokeObjectURL(entry.media.url);
    } catch (e) { setNotice(logError(e, 'Xóa kết quả').raw); }
    finally { setDeletingMedia(null); }
  }
  function invalidate(scene: Scene, scope: Output | 'both' = 'both'): Scene {
    const next = { ...scene };
    if (scope !== 'image') { releaseVideo(next.video); next.video = undefined; }
    if (scope !== 'video') { releaseVideo(next.image); next.image = undefined; }
    return { ...next, status: next[settings.output] ? 'done' : 'ready', error: undefined };
  }
  function changeScene(id: number, patch: Partial<Scene>, reset = true, scope: Output | 'both' = 'both') { updateScenes(all => all.map(s => s.id === id ? { ...(reset ? invalidate(s, scope) : s), ...patch } : s)); }
  function changeSettings(patch: Partial<Settings>, reset = true) {
    if (locked) return;
    const next = normalizeSettings({ ...settings, ...patch });
    commitSettings(next);
    if (patch.output) { updateScenes(all => all.map(s => ({ ...s, status: s[patch.output!] ? 'done' : 'ready', error: undefined }))); return; }
    if (reset) {
      const scope: Output | 'both' = patch.imageResolution ? 'image' : ('resolution' in patch || 'duration' in patch || 'model' in patch || 'videoInput' in patch) ? 'video' : 'both';
      updateScenes(all => all.map(s => invalidate(s, scope)));
    }
  }
  function imageReference(media: MediaResult, id: number): Reference { return { id: crypto.randomUUID(), name: `Ảnh đã tạo #${id}`, base64: media.base64, mimeType: media.mimeType, url: `data:${media.mimeType};base64,${media.base64}` }; }
  function useImagesForVideo(ids?: number[]) {
    if (locked) return;
    updateScenes(all => all.map(s => { const next = s.image && (!ids || ids.includes(s.id)) ? { ...invalidate(s, 'video'), reference: imageReference(s.image, s.id) } : s; return { ...next, status: next.video ? 'done' : 'ready', error: undefined }; }));
    commitSettings({ ...settingsRef.current, output: 'video', videoInput: 'image' });
    setNotice('Đã dùng ảnh đã tạo làm đầu vào video. Prompt và ảnh được giữ nguyên.');
  }
  function logError(error: unknown, scene: string) {
    const info = errorInfo(error);
    setLogs(all => [{ ...info, scene, time: new Date().toLocaleTimeString('vi-VN') }, ...all].slice(0, 30));
    return info;
  }
  useEffect(() => { void refreshStatus(); }, []);
  useEffect(() => { if (!busy) return; const timer = setInterval(() => { void refreshStatus(false); }, 1200); return () => clearInterval(timer); }, [busy]);
  useEffect(() => {
    let mounted = true;
    void loadMedia().then(entries => {
      if (!mounted) { entries.forEach(entry => URL.revokeObjectURL(entry.media.url)); return; }
      updateLibrary(() => entries);
      updateScenes(all => all.map(scene => {
        const image = entries.find(entry => entry.sceneId === scene.id && entry.media.kind === 'image' && matchesRequest(entry, scene, { ...settings, output: 'image' }))?.media;
        const video = entries.find(entry => entry.sceneId === scene.id && entry.media.kind === 'video' && matchesRequest(entry, { ...scene, image }, { ...settings, output: 'video' }))?.media;
        return { ...scene, image, video, status: (settings.output === 'image' ? image : video) ? 'done' : 'ready' };
      }));
    }).catch(e => { if (mounted) setNotice(`Chưa đọc được kho kết quả: ${errorInfo(e).raw}`); }).finally(() => { if (mounted) setLibraryLoading(false); });
    return () => { mounted = false; libraryRef.current.forEach(entry => URL.revokeObjectURL(entry.media.url)); };
  }, []);
  useEffect(() => window.museTransport?.onSessionRefresh?.(() => {
    if (usingBrowser && !locked) void connectAccount(true);
  }), [usingBrowser, locked, selectedAccount]);
  useEffect(() => {
    if (!usingBrowser || busy || diagnosticBusy || connectingId !== null || (sessionVerified && !['accounts', 'diagnostics'].includes(modal || ''))) return;
    const timer = setInterval(() => { void refreshStatus(false); }, 3000);
    return () => clearInterval(timer);
  }, [usingBrowser, modal, busy, diagnosticBusy, connectingId, sessionVerified]);
  useEffect(() => {
    try { localStorage.setItem(STORAGE, JSON.stringify({ version: 1, settings, scenes: scenes.map(({ prompt, enabled }) => ({ prompt, enabled })) })); }
    catch { setNotice('Trình duyệt không lưu được phiên. Hãy xuất dự án JSON để giữ kịch bản.'); }
  }, [scenes, settings]);
  useEffect(() => { if (!notice) return; const timer = setTimeout(() => setNotice(''), 7000); return () => clearTimeout(timer); }, [notice]);
  useEffect(() => () => { controller.current?.abort(); renderJobs.current.forEach(job => job.control.abort()); scenesRef.current.forEach(s => { releaseVideo(s.video); releaseVideo(s.image); }); }, []);

  function applyImage(image: Reference, target: number | 'global') {
    if (target === 'global') {
      setGlobalImage(image);
      if (settings.autoSync) updateScenes(all => all.map(s => ({ ...invalidate(s), reference: image })));
      setNotice(settings.autoSync ? 'Đã đồng bộ ảnh nhân vật cho cả 10 cảnh.' : 'Đã chọn ảnh chung. Bấm Áp dụng để gán cho 10 cảnh.');
    } else changeScene(target, { reference: image });
  }
  async function chooseImage(target: number | 'global') {
    if (locked) return;
    imageTarget.current = target; imageInput.current?.click();
  }
  async function handleImage(file?: File) {
    if (!file || locked) return;
    const target = imageTarget.current;
    setImageBusy(true);
    try { applyImage(await readImage(file), target); }
    catch (e) { setNotice(errorInfo(e).raw); }
    finally { setImageBusy(false); }
  }
  function beginBatch() {
    if (!renderBatch.current) {
      const control = new AbortController(); controller.current = control;
      renderBatch.current = { control, batchId: crypto.randomUUID(), completed: 0, failed: 0, cancelled: 0, loginRequired: false };
      setBusy(true); setCancelling(false);
    }
    return renderBatch.current;
  }
  function pumpRenders() {
    const batch = renderBatch.current;
    if (!batch) return;
    const jobs = renderJobs.current;
    const active = [...jobs.values()].filter(job => job.started);
    let running = active.length; let museRunning = active.filter(job => job.settings.mode === 'muse').length;
    for (const job of jobs.values()) {
      if (running >= 10 || batch.control.signal.aborted) break;
      if (job.started || (job.settings.mode === 'muse' && (job.settings.accountMode === 'multiple' ? active.some(other=>other.settings.mode==='muse' && other.accountId===job.accountId) : museRunning >= museLanes.current))) continue;
      job.started = true; running++; if (job.settings.mode === 'muse') museRunning++;
      void renderOne(job, batch);
    }
    if (jobs.size) return;
    setNotice(batch.control.signal.aborted ? 'Đã dừng các tác vụ. Yêu cầu Muse đã nhận có thể vẫn được tính phí.' : batch.loginRequired ? 'Có cảnh cần đăng nhập Muse lại. Kết nối lại rồi chạy phần chưa hoàn tất.' : `Đã xử lý: ${batch.completed} hoàn tất, ${batch.failed} lỗi, ${batch.cancelled} đã dừng.`);
    renderBatch.current = null; controller.current = null;
    setBusy(false); setBatch(false); setCancelling(false); void refreshStatus(false);
  }
  async function renderOne(job: RenderJob, batch: RenderBatch) {
    const { scene, control, settings: config } = job;
    let finalStatus: Status = 'ready'; let failure: string | undefined;
    changeScene(scene.id, { status: 'running', stopping: false, error: undefined }, false);
    try {
      control.signal.throwIfAborted();
      if (job.action === 'enhance') {
        const prompt = await enhancePrompt(scene.prompt, config.mode, control.signal, { batchId: batch.batchId, sceneId: scene.id, accountId: job.accountId, accountMode: config.accountMode });
        control.signal.throwIfAborted();
        if (scenesRef.current.find(value => value.id === scene.id)?.prompt === scene.prompt) changeScene(scene.id, { prompt });
        else setNotice('Prompt đã đổi trong lúc AI xử lý; tool giữ nội dung bạn đang sửa.');
      } else {
        const reference = scene.reference || (config.output === 'video' && config.videoInput === 'image' && scene.image ? imageReference(scene.image, scene.id) : null);
        const generate = config.output === 'image' ? generateImage : generateVideo;
        const media = await generate(scene.prompt, reference, config, control.signal, { batchId: batch.batchId, sceneId: scene.id, accountId: job.accountId, accountMode: config.accountMode });
        if (control.signal.aborted) { releaseVideo(media); throw new DOMException('Đã dừng', 'AbortError'); }
        const id = crypto.randomUUID();
        const entry: SavedMedia = { id, sceneId: scene.id, prompt: scene.prompt, createdAt: new Date().toISOString(), persisted: true, media: { ...media, savedId: id }, settings: config, referenceId: referenceKey(scene, config) };
        try { await saveMedia(entry); } catch (e) { entry.persisted = false; logError(e, `Lưu kết quả #${scene.id}`); }
        updateLibrary(all => [entry, ...all]);
        updateScenes(all => all.map(current => current.id === scene.id && matchesRequest(entry, current, { ...settingsRef.current, output: config.output }) ? { ...current, [config.output]: entry.media } : current));
      }
      batch.completed++;
    } catch (e) {
      if (control.signal.aborted) { finalStatus = 'cancelled'; batch.cancelled++; }
      else {
        const info = logError(e, `${job.action === 'enhance' ? 'Enhance' : config.output === 'image' ? 'Ảnh' : 'Video'} #${scene.id}`);
        failure = info.raw; finalStatus = 'error'; batch.failed++;
        if (/MUSE_LOGIN_REQUIRED/.test(info.raw)) batch.loginRequired = true;
        if (/MUSE_SHARED_CONVERSATION|MUSE_PARALLEL_UNVERIFIED/.test(info.raw)) {
          museLanes.current = 1;
          setStatus(current => current ? { ...current, executionConcurrency: 1 } : current);
        }
      }
    } finally {
      renderJobs.current.delete(scene.id);
      updateScenes(all => all.map(current => current.id === scene.id ? { ...current, enhancing: false, activeOutput: undefined, stopping: false,
        status: settingsRef.current.output === config.output && finalStatus !== 'ready' ? finalStatus : current[settingsRef.current.output] ? 'done' : 'ready',
        error: settingsRef.current.output === config.output ? failure : undefined } : current));
      pumpRenders();
    }
  }
  async function run(ids?: number[], override?: Scene[]) {
    if (renderLocked || (controller.current && !renderBatch.current) || renderBatch.current?.control.signal.aborted || !requireProvider()) return;
    const config = { ...settingsRef.current };
    const source = override || scenesRef.current;
    const targets = source.filter(scene => !renderJobs.current.has(scene.id) && scene.enabled && scene.prompt.trim() && sourceReady(scene) && accountReady(scene) && (ids ? ids.includes(scene.id) : !scene[config.output] || !matchesRequest(libraryRef.current.find(entry => entry.id === scene[config.output]?.savedId), scene, config)));
    if (!targets.length) return setNotice('Không có ô trống cần tạo; các ô đang chạy được giữ nguyên.');
    beginBatch();
    for (const scene of targets) renderJobs.current.set(scene.id, { accountId: config.accountMode === 'multiple' ? scene.id : 1, scene, settings: { ...config }, action: 'render', control: new AbortController(), started: false });
    setBatch(renderJobs.current.size > 1);
    updateScenes(all => all.map(scene => targets.some(target => target.id === scene.id) ? { ...scene, status: 'queued', stopping: false, error: undefined } : scene));
    setNotice(`${multipleAccounts ? 'Chỉ chạy các ô đã xác minh tài khoản. ' : ''}Đã thêm ${targets.length} cảnh ${config.output === 'image' ? 'ảnh' : 'video'}. Tác vụ giữ prompt và thiết lập tại lúc bấm Tạo.`);
    pumpRenders();
  }
  function cancelScene(id: number) {
    const job = renderJobs.current.get(id); const batch = renderBatch.current;
    if (!job || !batch || job.control.signal.aborted) return;
    job.control.abort();
    if (job.started) changeScene(id, { stopping: true }, false);
    else {
      renderJobs.current.delete(id); batch.cancelled++;
      changeScene(id, { status: 'cancelled', stopping: false, activeOutput: undefined, enhancing: false }, false); pumpRenders();
    }
  }
  async function enhance(scene: Scene) {
    if (renderLocked || renderJobs.current.has(scene.id) || !scene.prompt.trim() || !accountReady(scene) || settingsRef.current.mode === 'demo' || !requireProvider()) return;
    beginBatch();
    renderJobs.current.set(scene.id, { accountId: accountFor(scene.id), scene, settings: { ...settingsRef.current }, action: 'enhance', control: new AbortController(), started: false });
    setBatch(renderJobs.current.size > 1); updateScenes(all => all); pumpRenders();
  }
  function cancel() {
    setCancelling(true); controller.current?.abort();
    for (const id of [...renderJobs.current.keys()]) cancelScene(id);
  }
  async function downloadAll() {
    if (downloading || libraryLoading) return;
    setDownloading(true);
    try {
      const items = scenesRef.current.filter(scene => scene[settings.output]).map(scene => ({ media: scene[settings.output]!, id: scene.id }));
      const range = await downloadMediaBatch(items, settings.output);
      if (range.cancelled) setNotice('Đã hủy chọn thư mục lưu.');
      else setNotice(`Đã lưu ${items.length} ${outputLabel} vào thư mục · số ${range.first}–${range.last}.`);
    } catch (e) { setNotice(logError(e, 'Tải bộ kết quả').raw); }
    finally { setDownloading(false); }
  }
  function importScenes(andRun: boolean) {
    if (!canImport || locked || (andRun && !requireProvider())) return;
    const next = scenesRef.current.map((s, i) => ({ ...invalidate(s), prompt: parsed[i] || '' }));
    updateScenes(() => next); setModal(null);
    setNotice(`Đã nạp ${parsed.length} cảnh. ${10 - parsed.length} ô còn lại được để trống.`);
    if (andRun) void run(next.filter(s => s.prompt.trim()).map(s => s.id), next);
  }
  async function importFile(file?: File) {
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) return setNotice('Kịch bản tối đa 2 MB.');
    if (!/\.(txt|srt)$/i.test(file.name)) return setNotice('Chọn tệp .txt hoặc .srt UTF-8.');
    try { setImportText(await file.text()); } catch { setNotice('Không đọc được tệp kịch bản.'); }
  }
  async function diagnose() {
    if (controller.current || !diagnosticConsent || !requireProvider() || (multipleAccounts&&!sessionVerified)) return;
    setDiagnosticBusy(true); setDiagnostic(null);
    const control = new AbortController(); controller.current = control;
    const started = performance.now();
    try {
      const testSettings = normalizeSettings({ ...settings, duration: 4, resolution: '360p', imageResolution: '2k', videoInput: 'text', modifier: '', r2v: false });
      const generate = settings.output === 'image' ? generateImage : generateVideo;
      const video = await generate('A calm ocean at sunrise, gentle waves, cinematic composition.', null, testSettings, control.signal, {batchId:crypto.randomUUID(),sceneId:selectedAccount,accountId:multipleAccounts?selectedAccount:1,accountMode:settings.accountMode});
      releaseVideo(video);
      const requestLabel = settings.output === 'image' ? 'ảnh 2K' : `${testSettings.duration}s · ${testSettings.resolution}`;
      const actualLabel = video.metadata ? ` Muse trả về ${video.metadata.width}×${video.metadata.height}${typeof video.metadata.duration === 'number' ? `, ${video.metadata.duration.toFixed(1)}s` : ''}.` : '';
      setDiagnostic({ message: `${settings.mode === 'demo' ? 'Luồng kiểm thử' : 'Render thử'} hoàn tất sau ${((performance.now() - started) / 1000).toFixed(1)} giây. Yêu cầu ${requestLabel}.${actualLabel} Số dư xem trên bảng tài khoản; GPU: chưa có thông tin.` });
    } catch (e) { const info = logError(e, 'Chẩn đoán'); setDiagnostic({ message: info.hint, error: info.raw }); }
    finally { controller.current = null; setDiagnosticBusy(false); setCancelling(false); void refreshStatus(); }
  }
  function exportProject() {
    const blob = new Blob([JSON.stringify({ version: 1, settings, scenes: scenes.map(({ prompt, enabled }) => ({ prompt, enabled })) }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'muse-studio-project.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  async function restoreProject(file?: File) {
    if (!file || locked) return;
    if (file.size > 2 * 1024 * 1024) return setNotice('Dự án tối đa 2 MB.');
    try { const text = await file.text(); const value = JSON.parse(text);
      if (value.version !== 1 || !Array.isArray(value.scenes) || value.scenes.length !== 10) throw new Error('Dự án không đúng định dạng Muse Studio v1 (10 cảnh).');
      const restored = restoreWorkspace(text); updateScenes(all => { all.forEach(s => { releaseVideo(s.video); releaseVideo(s.image); }); return restored.scenes; }); commitSettings(restored.settings); setGlobalImage(null); setNotice('Đã mở dự án. Chọn lại ảnh tham chiếu; video và ảnh không lưu trong JSON.');
    } catch (e) { setNotice(errorInfo(e).raw); }
  }
  const connection = multipleAccounts && usingBrowser ? `Muse · ${status?.accounts?.filter(hasVerifiedSession).length || 0}/10 tài khoản đã xác minh` : settings.mode === 'demo' ? 'Kiểm thử · không dùng AI' : usingBrowser ? (hasVerifiedSession(primaryAccount) ? 'Muse · Đã xác minh' : 'Muse · Chưa xác minh') : status?.museConfigured ? 'Đã khai báo adapter Muse' : 'Chưa kết nối Muse AI';
  const composerFeedback = composerCheck && <div className="composer-feedback" role="status"><p>{composerCheck.message}</p>{(composerCheck.error || composerCheck.details) ? <details><summary>Chi tiết trang luồng</summary><pre>{composerCheck.error || JSON.stringify(composerCheck.details, null, 2)}</pre></details> : null}</div>;

  return <div className="app-shell">
    <input ref={imageInput} type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={e => { void handleImage(e.target.files?.[0]); e.target.value = ''; }}/>
    <input ref={fileInput} type="file" accept=".txt,.srt" hidden onChange={e => { void importFile(e.target.files?.[0]); e.target.value = ''; }}/>
    <header className="topbar">
      <div className="studio-tabs" aria-label="Loại nội dung"><button disabled={locked} aria-pressed={settings.output === 'video'} onClick={() => changeSettings({ output: 'video' })}><Video size={17}/>Tạo video</button><button disabled={locked} aria-pressed={settings.output === 'image'} onClick={() => changeSettings({ output: 'image' })}><ImagePlus size={17}/>Tạo ảnh hàng loạt</button><span>MUSE AI STUDIO · ẢNH / VIDEO</span></div>
      <div className="actions-row">
        <button className="button primary" title={renderBlocked ? connectionProblem : `Thêm các ô còn trống · ${executionLanes} luồng xử lý`} disabled={renderLocked || !enabled || renderBlocked || !scenes.some(scene => scene.enabled && scene.prompt.trim() && !renderJobs.current.has(scene.id) && sourceReady(scene) && accountReady(scene) && (!scene[settings.output] || !matchesRequest(libraryRef.current.find(entry => entry.id === scene[settings.output]?.savedId), scene, settings)))} onClick={() => void run()}><Play size={17} fill="currentColor"/>TẠO 10 {outputLabel.toLocaleUpperCase('vi')}</button>
        {busy && <button className="button danger" onClick={cancel} disabled={cancelling}><Square size={16}/>{cancelling ? 'Đang dừng…' : batch ? 'Dừng tất cả luồng' : 'Dừng tác vụ'}</button>}
        <button className="button" title="Lưu các kết quả đang chọn vào một thư mục thường, tự đánh số tiếp" disabled={!done || downloading || libraryLoading} onClick={() => void downloadAll()}><Download size={17}/>{downloading ? 'Đang lưu thư mục…' : `Tải tất cả (${done}/10)`}</button>
        <button className="button" disabled={downloading} onClick={() => void chooseExportDirectory().then(result => { if (!result.cancelled) setNotice(`Đã chọn nơi lưu: ${result.name}`); }).catch(error => setNotice(logError(error,'Chọn thư mục').raw))}><FolderOpen size={17}/>Thư mục lưu</button>
        <button className="button" disabled={locked} onClick={() => setModal('import')}><FileText size={18}/>Nhập TXT / SRT</button>
        <button className="button" onClick={() => setModal('accounts')}><Users size={19}/>Tài khoản Muse</button>
        <button className="button diagnostic-button" onClick={() => setModal('diagnostics')}><ShieldPlus size={19}/>Chẩn đoán API</button>
        <span className={`connection-pill ${settings.mode === 'demo' ? 'is-demo' : providerReady ? 'connected' : ''}`} title="Mở Chẩn đoán API để cấu hình kết nối"><i/>{connection}</span>
      </div>
      <div className="settings-row">
        {settings.output === 'video' && <><label className="setting model-setting"><span>MODEL:</span><select aria-label="Model AI" disabled={locked} value={settings.model} onChange={e => changeSettings({ model: e.target.value as Settings['model'] })}>{MUSE_MODELS.map(model => <option key={model} value={model}>{model}</option>)}</select></label><div className="setting"><span>NGUỒN:</span><div className="segmented"><button disabled={locked} aria-pressed={settings.videoInput === 'text'} onClick={() => changeSettings({ videoInput: 'text' })}>Từ prompt</button><button disabled={locked} aria-pressed={settings.videoInput === 'image'} onClick={() => changeSettings({ videoInput: 'image' })}>Từ ảnh</button></div></div></>}
        <div className="setting"><span>KHUNG:</span><div className="segmented">{(['16:9', '9:16'] as const).map(ratio => <button key={ratio} disabled={locked} aria-pressed={settings.aspectRatio === ratio} onClick={() => changeSettings({ aspectRatio: ratio })}>{ratio}</button>)}</div></div>
        {settings.output === 'video' ? <><label className="setting"><span>THỜI LƯỢNG:</span><select aria-label="Thời lượng" value={settings.duration} disabled={locked || settings.model !== 'Omni 1.1 Flash'} onChange={e => changeSettings({ duration: Number(e.target.value) })}>{[4, 6, 8, 10].map(n => <option key={n} value={n}>{n} giây</option>)}</select></label><label className="setting"><span>ĐỘ NÉT VIDEO:</span><select aria-label="Chất lượng" value={settings.resolution} disabled={locked} onChange={e => changeSettings({ resolution: e.target.value as Settings['resolution'] })}><option value="360p">360p (Thử nhanh)</option><option value="720p">720p · HD</option><option value="1080p">1080p · Full HD</option><option value="2k">2K · 2560×1440</option><option value="4k">4K · 3840×2160</option></select></label></> : <label className="setting"><span>ĐỘ NÉT ẢNH:</span><select aria-label="Độ nét ảnh" value={settings.imageResolution} disabled={locked} onChange={e => changeSettings({ imageResolution: e.target.value as Settings['imageResolution'] })}><option value="2k">2K · 2560px cạnh dài</option><option value="4k">4K · 3840px cạnh dài</option></select></label>}
        <div className="setting sync-setting"><label className="checkbox-label"><input type="checkbox" checked={settings.r2v} disabled={locked} onChange={e => changeSettings({ r2v: e.target.checked })}/>Đồng nhất nhân vật</label><button className="micro-button" disabled={locked} onClick={() => void chooseImage('global')}>+ Chọn ảnh</button></div>
      </div>
    </header>

    <main>
      {renderBlocked && <section className="connection-warning" aria-label="Cần kết nối tạo video"><CircleAlert size={20}/><div><strong>{settings.mode === 'muse' && statusLoading ? 'Đang kiểm tra kết nối' : 'Chưa thể tạo ảnh/video AI'}</strong><p>{connectionProblem}</p><p>Kịch bản và ảnh vẫn có thể chỉnh sửa. Tạo ảnh/video và AI Enhance sẽ bật sau khi có kết nối phù hợp.</p></div><button className="button" onClick={() => setModal(usingBrowser ? 'accounts' : 'diagnostics')}>{usingBrowser ? 'Kết nối tài khoản Muse' : 'Xem cách kết nối'}</button></section>}
      {usingBrowser && settings.mode === 'muse' && <p className="transport-note">Muse nhận mô hình, thời lượng và tỉ lệ dưới dạng yêu cầu trong prompt. Ảnh/video hiển thị kích thước thật; nếu Muse trả thấp hơn 2K/4K, tool sẽ ghi Chưa đạt yêu cầu.</p>}
      {settings.mode === 'demo' && <div className="demo-banner"><FlaskConical size={16}/>CHẾ ĐỘ KIỂM THỬ · Dùng tệp mẫu 640×360 có nhãn. Không tạo nội dung AI từ prompt hoặc ảnh.</div>}
      <section className="account-mode-bar" aria-label="Lựa chọn chế độ tài khoản"><label>Chế độ tài khoản <select aria-label="Chế độ tài khoản" disabled={connectionLocked} value={settings.accountMode} onChange={e=>{changeSettings({accountMode:e.target.value as Settings['accountMode']},false);if(e.target.value==='single')void selectAccount(1)}}><option value="single">1 tài khoản · tối đa 10 luồng</option><option value="multiple" disabled={!status?.multiAccount}>10 tài khoản · mỗi tài khoản 1 luồng</option></select></label><button className="button" onClick={()=>setModal('accounts')}><Users size={17}/>Quản lý 10 tài khoản</button>{multipleAccounts && <span>Muse 01 → ô 01 · Muse 02 → ô 02 · … · Muse 10 → ô 10</span>}</section>
      <section className="single-account-panel" aria-label="Một tài khoản Muse và số dư">
        <div><span className="eyebrow">{multipleAccounts ? 'MỖI TÀI KHOẢN MỘT LUỒNG' : 'MỘT TÀI KHOẢN DUY NHẤT'}</span><h2>{multipleAccounts ? '10 tài khoản · 10 luồng độc lập' : 'Một tài khoản · 10 cảnh'}</h2><p>Bấm Tạo 10 để chạy toàn bộ kịch bản. Hiện xử lý {executionLanes} cảnh mỗi lượt; các cảnh còn lại chờ trong hàng đợi. {executionLanes === 1 ? 'Gửi lần lượt để tránh trộn kết quả trong hội thoại chung.' : 'Xử lý song song theo khả năng của kết nối hiện tại.'}</p>{usingBrowser && !multipleAccounts && settings.mode === 'muse' && <div className="concurrency-controls"><label htmlFor="muse-concurrency">Số luồng:</label><select id="muse-concurrency" disabled={connectionLocked || !hasVerifiedSession(primaryAccount)} value={executionLanes} onChange={e => void changeConcurrency(Number(e.target.value))}>{[1,2,3,5,10].map(count => <option key={count} value={count}>{count === 1 ? '1 · Lần lượt' : `${count} · Kiểm tra và bật song song`}</option>)}</select><small>Chỉ bật khi tìm được hội thoại riêng. Hạn mức render do Muse quyết định.</small></div>}</div>
        <div className="single-account-controls">{status?.multiAccount && <label>Tài khoản đang chọn <select aria-label="Tài khoản đang chọn" disabled={connectionLocked} value={selectedAccount} onChange={e=>void selectAccount(Number(e.target.value))}>{status.accounts?.map(account=><option key={account.id} value={account.id}>{String(account.id).padStart(2,'0')} · {account.label}</option>)}</select></label>}<strong className={providerReady ? 'mint' : 'muted'}>{usingBrowser ? accountStateName(museAccount) : connection}</strong><button className="button" disabled={connectionLocked || !usingBrowser} onClick={() => void connectAccount()}><Link2 size={15}/>{connectingId !== null ? 'Đang kết nối…' : embeddedLogin ? 'Đăng nhập Muse trong tool' : 'Kết nối Muse'}</button><button className="micro-button" disabled={connectionLocked || !usingBrowser} onClick={() => void connectAccount(true)}>Kiểm tra phiên</button><button className="micro-button" disabled={connectionLocked || !usingBrowser || !sessionVerified} onClick={() => void checkComposer()}>Kiểm tra ô Message</button><p className="connection-feedback" role="status">{connectingId !== null ? 'Đang kiểm tra phiên Muse…' : connectionError || museAccount?.connectionMessage || (hasVerifiedSession(museAccount) ? 'Phiên Muse đã được xác minh.' : 'Hoàn tất đăng nhập trong tab Muse rồi quay về Studio để tự kết nối.')}</p>{composerFeedback}</div>
        <div className="balance-card" data-testid="account-balance"><span>SỐ DƯ TÀI KHOẢN MUSE</span><strong>{settings.mode === 'demo' ? 'Chế độ kiểm thử' : balanceAccount?.balance ? `${balanceAccount.balance.valueText} ${balanceAccount.balance.unit}` : 'Chưa đọc được'}</strong><small>{balanceAccount?.balance ? `Đọc lúc ${new Date(balanceAccount.balance.observedAt).toLocaleTimeString('vi-VN')}` : 'Không tự suy đoán token hoặc credit'}</small><button className="micro-button" disabled={connectionLocked || !usingBrowser || !hasVerifiedSession(museAccount)} onClick={() => void connectAccount(true)}><RefreshCw size={12}/>Cập nhật số dư</button></div>
      </section>
      <section className="character-banner" aria-label="Đồng nhất nhân vật">
        <button className={`global-image ${globalImage ? 'has-image' : ''}`} disabled={locked} onClick={() => void chooseImage('global')} aria-label={globalImage ? 'Đổi ảnh nhân vật chung' : 'Tải ảnh nhân vật chung'}>
          {globalImage?.url ? <img src={globalImage.url} alt="Ảnh nhân vật chung"/> : <><ImagePlus size={22}/><span>{globalImage ? 'Đổi ảnh' : 'Tải ảnh NV'}</span></>}
        </button>
        <div className="character-copy"><h1><ScanFace size={22}/>ẢNH THAM CHIẾU NHÂN VẬT / ẢNH ĐẦU VÀO <span className="tag">R2V Reference</span></h1><p>{globalImage ? globalImage.name : 'Chọn ảnh chân dung để giữ nhân vật, hoặc ảnh nguồn cho video. Bỏ Đồng nhất nhân vật để Muse tạo độc lập theo từng prompt.'}</p>{globalImage && <div className="image-actions"><button disabled={locked} onClick={() => void chooseImage('global')}>Đổi ảnh khác</button><button disabled={locked} onClick={() => { const old = globalImage; setGlobalImage(null); updateScenes(all => all.map(s => s.reference?.id === old.id ? { ...invalidate(s), reference: null } : s)); }}>Gỡ ảnh chung</button></div>}</div>
        <label className="auto-sync"><input type="checkbox" disabled={locked} checked={settings.autoSync} onChange={e => { changeSettings({ autoSync: e.target.checked }, false); if (e.target.checked && globalImage) updateScenes(all => all.map(s => ({ ...invalidate(s), reference: globalImage }))); }}/><span><b>Bật đồng nhất tự động</b><small>{settings.autoSync ? 'Đang bật R2V khung' : 'Gán ảnh thủ công'}</small></span></label>
        <button className="button apply-all" disabled={locked || !globalImage} onClick={() => { updateScenes(all => all.map(s => ({ ...invalidate(s), reference: globalImage }))); setNotice('Đã áp dụng ảnh chung cho cả 10 cảnh.'); }}><Users size={18}/>Áp dụng cho 10 cảnh</button>
      </section>

      <section className="workstation-heading">
        <div className="studio-icon"><Video size={23}/></div><div className="heading-copy"><h2>10-SLOT {settings.output === 'image' ? 'IMAGE' : 'VIDEO'} WORKSTATION <span className="tag">MUSE STUDIO ENGINE</span></h2><p>Điều phối 10 phân cảnh · Model yêu cầu: <span>{settings.output === 'image' ? 'Muse tạo ảnh' : settings.model}</span> · Gửi yêu cầu và ảnh đến Muse; tính năng khả dụng do Muse quyết định.</p></div>
        <div className="progress-box"><span>{busy ? `${runningCount}/10 luồng đang chạy` : 'Tiến độ tạo:'}</span><div className="progress-track" role="progressbar" aria-label="Tiến độ tạo" aria-valuemin={0} aria-valuemax={10} aria-valuenow={done}><div style={{ width: `${done * 10}%` }}/></div><b>{done}/10</b></div>
      </section>

      {busy && usingBrowser && <p className="transport-note" role="status">Tool: {actualProgress.filter(stage => stage.active && !stage.submitted).length} ô đang mở · {actualProgress.filter(stage => stage.submitted).length} prompt đã hiển thị trên trang Muse. Các ô đang chạy: {runningCount}. Muse quyết định thời gian xử lý và trả kết quả.</p>}
      {settings.output === 'image' && scenes.some(s => s.image) && <div className="image-batch-actions"><button className="button" disabled={locked} onClick={() => useImagesForVideo()}><Video size={16}/>Chuyển bộ ảnh đã tạo sang video</button><span>Giữ ảnh và prompt, dùng ảnh đã tạo làm khung hình đầu.</span></div>}
      <section className="scene-grid" aria-label="10 phân cảnh ảnh và video">{scenes.map(scene => {
        const media = scene[settings.output];
        const history = library.filter(entry => entry.sceneId === scene.id && entry.media.kind === settings.output);
        const sceneBusy = scene.status === 'running' || scene.status === 'queued';
        const needsSource = settings.output === 'video' && settings.videoInput === 'image' && !scene.reference && !scene.image;
        const quality = media ? meetsResolution(media) : null;
        return <article key={scene.id} className={`scene-card ${!scene.enabled ? 'disabled-card' : ''} status-${scene.status}`} data-testid={`scene-${scene.id}`}>
          <header className="scene-header"><span className="scene-number">#{String(scene.id).padStart(2, '0')}</span><span className={`status-badge ${scene.status}`}>{scene.status === 'running' && <LoaderCircle className="spin" size={10}/>}{statusNames[scene.status]}</span><label className="scene-enable"><input type="checkbox" aria-label={`Bật cảnh ${scene.id}`} checked={scene.enabled} disabled={locked} onChange={e => changeScene(scene.id, { enabled: e.target.checked }, false)}/>Bật</label><span className="same-account-tag" title={status?.accounts?.find(account=>account.id===accountFor(scene.id))?.label}>{multipleAccounts ? `Muse ${String(scene.id).padStart(2,'0')}` : 'Muse'}</span></header>
          <div className="card-content">{multipleAccounts && settings.mode==='muse' && !accountReady(scene) && <p className="source-note red">Chưa xác minh Muse {String(scene.id).padStart(2,'0')}. <button className="micro-button" disabled={connectionLocked} onClick={()=>void connectAccount(false,scene.id)}>Đăng nhập</button></p>}
            {sceneBusy && <p className="source-note">{scene.enhancing ? 'AI Enhance' : scene.activeOutput === 'image' ? 'Tác vụ ảnh' : 'Tác vụ video'} đang dùng bản chụp thiết lập lúc bắt đầu. Bạn có thể sửa cho lượt tiếp theo.</p>}
            <div className="video-preview">{media ? <>{media.kind === 'image' ? <button className="image-open" aria-label={`Xem ảnh cảnh ${scene.id}`} onClick={() => { setViewerNatural(false); setViewer({ id: scene.id, media }); }}><img className="generated-image" src={media.url} alt={`Ảnh kết quả cảnh ${scene.id}`}/></button> : <video src={media.url} controls playsInline preload="metadata" aria-label={`Video cảnh ${scene.id}`}/>} {media.demo && <span className="preview-label">{media.kind === 'image' ? 'ẢNH KIỂM THỬ' : 'CLIP KIỂM THỬ'}</span>}</> : <div className="empty-video">{scene.status === 'running' ? <LoaderCircle className="spin" size={25}/> : settings.output === 'image' ? <ImagePlus size={23}/> : <Clapperboard size={23}/>}<span>{scene.status === 'running' ? scene.enhancing ? 'Đang trau chuốt prompt…' : `Đang tạo ${scene.activeOutput === 'image' ? 'ảnh' : 'video'}…` : scene.status === 'queued' ? 'Đang chờ đến lượt…' : scene.status === 'error' ? `Tạo ${outputLabel} thất bại` : !scene.enabled ? 'Cảnh đã tắt' : `Chưa khởi tạo ${outputLabel}`}</span>{scene.status === 'running' && <small>Có thể mất vài phút</small>}</div>}</div>
            {history.length > 0 && <details className="media-history" open={history.length > 1}><summary>Kết quả đã lưu ({history.length})</summary><div className="history-grid">{history.map((entry, index) => <div className={`history-entry ${entry.id === media?.savedId ? 'selected' : ''}`} key={entry.id}>
              <button className="history-select" disabled={deletingMedia !== null} aria-label={`Xem bản ${history.length - index} cảnh ${scene.id}`} aria-pressed={entry.id === media?.savedId} title={entry.prompt} onClick={() => selectResult(entry)}>{entry.media.kind === 'image' ? <img src={entry.media.url} alt={`Bản ${history.length - index} cảnh ${scene.id}`} loading="lazy"/> : <Film size={25}/>}<span>Bản {history.length - index}{entry.media.demo ? ' · Kiểm thử' : ''}</span></button>
              <small>{new Date(entry.createdAt).toLocaleString('vi-VN')}</small>{!entry.persisted && <small className="red">Chưa lưu trên ổ đĩa · hãy tải ngay</small>}<p title={entry.prompt}>{entry.prompt}</p>
              <div className="history-actions"><button aria-label={`Tải bản ${history.length - index} cảnh ${scene.id}`} onClick={() => void downloadVideo(entry.media, scene.id).catch(e => setNotice(logError(e, 'Tải kết quả').raw))}><Download size={12}/>Tải</button><button disabled={downloading || deletingMedia !== null} aria-label={`Xóa bản ${history.length - index} cảnh ${scene.id}`} onClick={() => void removeResult(entry)}><Trash2 size={12}/>Xóa</button></div>
            </div>)}</div></details>}
            {media?.metadata && <p className="video-metadata">Muse trả về: {media.metadata.width}×{media.metadata.height}{typeof media.metadata.duration === 'number' ? ` · ${media.metadata.duration.toFixed(1)} giây` : ''}</p>}
            {quality !== null && <p className={`quality-result ${quality ? 'mint' : 'red'}`}>{quality ? 'Kích thước đạt' : 'Chưa đạt yêu cầu'} {media?.requestedResolution?.toUpperCase()}</p>}
            {media?.referenceCompressed && <p className="source-note">Ảnh đầu vào đã nén dưới 8 MB; ảnh gốc được giữ.</p>}
            {media?.kind === 'image' && <button className="micro-button animate-image" disabled={locked} onClick={() => useImagesForVideo([scene.id])}><Video size={12}/>Dùng ảnh này tạo video</button>}
            <div className="reference-box"><div className="reference-heading"><ScanFace size={19}/><span>{settings.output === 'video' && settings.videoInput === 'image' ? 'Ảnh đầu vào:' : 'Ảnh nhân vật:'}</span>{scene.reference && <button className="remove-image" aria-label={`Gỡ ảnh cảnh ${scene.id}`} disabled={locked} onClick={() => changeScene(scene.id, { reference: null })}><X size={12}/></button>}</div>
              {scene.reference ? <button className="scene-image" disabled={locked} aria-label={`Đổi ảnh cảnh ${scene.id}`} onClick={() => void chooseImage(scene.id)}><img src={scene.reference.url} alt={`Nhân vật cảnh ${scene.id}`}/><span>{scene.reference.id === globalImage?.id ? 'Ảnh chung · đã đồng bộ' : 'Ảnh riêng'}<small>Nhấn để đổi ảnh</small></span></button> : <button className="select-image" disabled={locked} onClick={() => void chooseImage(scene.id)}><ImagePlus size={18}/>+ Chọn ảnh nhân vật</button>}
              {globalImage && scene.reference?.id !== globalImage.id && <button className="paste-image" disabled={locked} onClick={() => changeScene(scene.id, { reference: globalImage })}><Copy size={10}/>Dùng ảnh chung</button>}
              {needsSource && <p className="source-note red">Cần ảnh đầu vào để tạo video từ ảnh.</p>}
              {!settings.r2v && !(settings.output === 'video' && settings.videoInput === 'image') && <p className="source-note">Theo prompt độc lập · không gửi ảnh nhân vật.</p>}
            </div>
            <div className="prompt-label"><label htmlFor={`prompt-${scene.id}`}>Kịch bản Prompt:</label><button disabled={renderLocked || sceneBusy || !accountReady(scene) || settings.mode === 'demo' || !scene.prompt.trim() || !scene.enabled} onClick={() => void enhance(scene)} title="Dịch và trau chuốt prompt bằng AI">{scene.enhancing ? <LoaderCircle size={18} className="spin"/> : <WandSparkles size={19}/>}AI Enhance</button></div>
            <textarea id={`prompt-${scene.id}`} aria-label={`Kịch bản cảnh ${scene.id}`} disabled={locked || scene.enhancing} maxLength={8000} value={scene.prompt} onChange={e => changeScene(scene.id, { prompt: e.target.value })} placeholder="Nhập mô tả phân cảnh…"/>
            {scene.error && <div className="scene-error"><span><CircleAlert size={13}/>{errorInfo(scene.error).hint}</span><details><summary>Mã lỗi gốc</summary><pre>{scene.error}</pre></details></div>}
          </div>
          <footer className="card-footer">{scene.status === 'running' || scene.status === 'queued' ? <button className="scene-run scene-stop" disabled={scene.stopping || cancelling} aria-label={`Dừng cảnh ${scene.id}`} onClick={() => cancelScene(scene.id)}>{scene.stopping ? <LoaderCircle className="spin" size={15}/> : <Square size={15}/>} {scene.stopping ? 'Đang dừng…' : scene.status === 'queued' ? 'Hủy cảnh chờ' : 'Dừng cảnh này'}</button> : <button className={`scene-run ${media ? 'has-result' : ''}`} disabled={renderLocked || !accountReady(scene) || !scene.enabled || !scene.prompt.trim() || needsSource} onClick={() => void run([scene.id])}>{media || scene.status === 'error' ? <RefreshCw size={15}/> : <Play size={15}/>} {media ? 'Tạo lại cảnh' : scene.status === 'error' ? 'Thử lại cảnh này' : 'Tạo cảnh này'}</button>}{media && <button className="download-one" title={`Tải cảnh ${scene.id}`} aria-label={`Tải cảnh ${scene.id}`} onClick={() => void downloadVideo(media, scene.id).catch(e => setNotice(logError(e, 'Tải tệp').raw))}><Download size={16}/></button>}</footer>
        </article>;
      })}</section>
      <footer className="workspace-footer"><span><i/>Tự lưu kịch bản trên trình duyệt <span className="footer-divider">/</span> Ảnh & video lưu trên máy trong từng ô</span><div><label className={`footer-button ${locked ? 'muted' : ''}`}><Upload size={13}/>Mở dự án<input type="file" accept=".json" hidden disabled={locked} onChange={e => { void restoreProject(e.target.files?.[0]); e.target.value = ''; }}/></label><button onClick={exportProject}><Download size={13}/>Xuất dự án JSON</button></div></footer>
    </main>
    {notice && <div className="toast" role="status"><CircleAlert size={17}/><span>{notice}</span><button aria-label="Đóng thông báo" onClick={() => setNotice('')}><X size={15}/></button></div>}

    {modal === 'import' && <Modal title="Nhập kịch bản thông minh" eyebrow="SCRIPT IMPORT / 10 SCENES" close={() => setModal(null)}>
      <div className="modal-body"><p className="muted">TXT: mỗi dòng hoặc mỗi đoạn là một cảnh. SRT: mỗi khối phụ đề là một cảnh, tự bỏ số thứ tự và timestamp. Tối đa 10 cảnh.</p><div className="preset-row"><button className="button" onClick={() => setImportText(ADVENTURE.join('\n\n'))}><Film size={16}/>Điện ảnh phiêu lưu</button><button className="button" onClick={() => setImportText(RUNWAY.join('\n\n'))}><WandSparkles size={16}/>Thời trang Runway</button><button className="button" onClick={() => fileInput.current?.click()}><Upload size={16}/>Chọn TXT / SRT</button></div>
        <textarea className="import-text" aria-label="Nội dung TXT / SRT" value={importText} onChange={e => setImportText(e.target.value)} placeholder={'Dán kịch bản hoặc phụ đề vào đây…\n\n1\n00:00:00,000 --> 00:00:04,000\nMột người thám hiểm bước vào ngôi đền cổ.'}/>
        <div className="import-count"><b className={parsed.length > 10 ? 'red' : 'mint'}>{parsed.length}/10 cảnh</b><span>{parsed.length > 10 ? 'Có hơn 10 cảnh. Rút gọn trước khi nạp, không tự cắt bỏ nội dung.' : parsed.length < 10 ? 'Các ô còn lại sẽ được để trống.' : 'Đã đủ 10 phân cảnh.'}</span></div>
        <div className="script-preview">{parsed.slice(0, 10).map((text, i) => <div key={i}><span>#{String(i + 1).padStart(2, '0')}</span><p>{text}</p></div>)}</div><p className="small muted">Nạp kịch bản sẽ thay prompt và xóa kết quả ảnh/video cũ của 10 cảnh. Giữ ảnh tham chiếu và tài khoản.</p>
      </div><footer className="modal-footer"><button className="button" onClick={() => setModal(null)}>Đóng</button><button className="button" disabled={!canImport || locked} onClick={() => importScenes(false)}>Nạp vào Studio</button><button className="button primary" disabled={!canImport || locked || renderBlocked} onClick={() => importScenes(true)}><Play size={15}/>Nạp & Chạy các cảnh</button></footer>
    </Modal>}

    {viewer && <Modal title={`Xem ảnh cảnh ${viewer.id}`} eyebrow="ẢNH KẾT QUẢ" wide close={() => setViewer(null)}>
      <div className={`viewer-canvas ${viewerNatural ? 'natural' : ''}`}><img src={viewer.media.url} alt={`Ảnh lớn cảnh ${viewer.id}`}/></div>
      <footer className="modal-footer"><span className="small muted">{viewer.media.metadata ? `${viewer.media.metadata.width}×${viewer.media.metadata.height}` : 'Ảnh đã tạo'}</span><button className="button" aria-pressed={viewerNatural} onClick={() => setViewerNatural(value => !value)}>{viewerNatural ? 'Vừa cửa sổ' : 'Kích thước gốc'}</button><button className="button primary" onClick={() => void downloadVideo(viewer.media, viewer.id).catch(error => setNotice(logError(error,'Tải ảnh đang xem').raw))}><Download size={15}/>Tải ảnh đang xem</button></footer>
    </Modal>}

    {modal === 'accounts' && <Modal title="Quản lý tài khoản Muse" eyebrow="ONE ACCOUNT / 10 SCENES" close={() => setModal(null)}>
      <div className="modal-body"><div className="info-note"><Users size={18}/><span>Giữ cả hai chế độ: một tài khoản cho 10 ô hoặc 10 tài khoản riêng, mỗi tài khoản một ô. Chọn chế độ trên bảng chính. Mỗi phiên đăng nhập được lưu riêng trên máy.</span></div>
        <div className="single-account-dialog"><strong className={providerReady ? 'mint' : 'muted'}>{usingBrowser ? accountStateName(museAccount) : connection}</strong><p className="muted">Đang chọn Muse {String(selectedAccount).padStart(2,'0')}. Đăng nhập trên trang Muse trong {loginPlace}, bấm Về Studio rồi Kiểm tra phiên. Muse có thể giới hạn số tác vụ đồng thời hoặc hạn mức của tài khoản.</p>{usingBrowser && <div className="preset-row"><button className="button primary" disabled={connectionLocked} onClick={() => void connectAccount()}><Link2 size={16}/>{embeddedLogin ? 'Đăng nhập Muse trong tool' : 'Mở cửa sổ Muse'}</button><button className="button" disabled={connectionLocked} onClick={() => void connectAccount(true)}>Kiểm tra phiên Muse</button><button className="button" disabled={connectionLocked || !sessionVerified} onClick={() => void checkComposer()}>Kiểm tra ô Message</button></div>}{composerFeedback}</div>
        {status?.multiAccount && <><div className="account-import"><button className="button" disabled={connectionLocked} onClick={()=>void checkAllAccounts()}>Kiểm tra 10 phiên</button><label className="field-label" htmlFor="account-list">Nhập danh sách tài khoản</label><p className="small muted">Mỗi dòng một email hoặc tên quản lý, tối đa 10 dòng. Danh sách chỉ đặt nhãn cho Muse 01–10; đăng nhập từng tài khoản trên trang Muse để xác thực bằng email/OTP. Không nhập mật khẩu, mã xác nhận hoặc token vào danh sách này.</p><textarea id="account-list" aria-label="Danh sách 10 tài khoản" disabled={connectionLocked} value={accountList} onChange={e=>setAccountList(e.target.value)} placeholder={'taikhoan1@example.com\ntaikhoan2@example.com'}/><div className="preset-row"><label className="button upload-project">Nhập TXT<input type="file" accept=".txt" hidden disabled={connectionLocked} onChange={e=>{const file=e.target.files?.[0];if(file&&file.size<=16384)void file.text().then(setAccountList);else if(file)setNotice('Danh sách tài khoản tối đa 16 KB.');e.target.value=''}}/></label><button className="button" disabled={connectionLocked||!accountList.trim()} onClick={()=>void importAccounts()}>Lưu danh sách</button></div></div><div className="account-grid">{status.accounts?.map(account=><article className="account-item" key={account.id}><strong>Muse {String(account.id).padStart(2,'0')} · Ô {String(account.id).padStart(2,'0')}</strong><span title={account.label}>{account.label}</span><small className={hasVerifiedSession(account)?'mint':'muted'}>{accountStateName(account)}</small><small>{account.balance?`${account.balance.valueText} ${account.balance.unit}`:'Chưa đọc được số dư'}</small><div><button className="button" aria-label={`Đăng nhập Muse ${account.id}`} disabled={connectionLocked} onClick={()=>void connectAccount(false,account.id)}>Đăng nhập</button><button className="micro-button" aria-label={`Kiểm tra Muse ${account.id}`} disabled={connectionLocked} onClick={()=>void connectAccount(true,account.id)}>Kiểm tra phiên</button></div></article>)}</div></>}
        <label className="field-label" htmlFor="global-modifier">Chỉ thị chất lượng toàn cục <span className="tag">GLOBAL PROMPT MODIFIER</span></label><textarea id="global-modifier" className="bulk-text" disabled={locked} maxLength={2000} value={settings.modifier} onChange={e => changeSettings({ modifier: e.target.value })} placeholder="cinematic lighting, photorealistic, professional 35mm lens…"/><p className="small muted">Nối vào cuối mọi prompt tạo ảnh/video. Thay đổi chỉ thị sẽ xóa kết quả cũ để tránh dùng video không còn khớp kịch bản.</p>
      </div><footer className="modal-footer"><span className="small muted">{enabled}/10 cảnh đang bật · Tự lưu</span><button className="button primary" onClick={() => setModal(null)}><Check size={16}/>Hoàn tất</button></footer>
    </Modal>}

    {modal === 'diagnostics' && <Modal title="Chẩn đoán & kết nối API" eyebrow="CONNECTION / HEALTH / ERROR LOG" close={() => setModal(null)}>
      <div className="modal-body"><label className="field-label" htmlFor="provider-mode">Kết nối tạo video</label><select id="provider-mode" className="provider-select" disabled={locked} value={settings.mode} onChange={e => { const mode = e.target.value as Mode; changeSettings({ mode }); setDiagnostic(null); setDiagnosticConsent(false); }}><option value="muse">{usingBrowser ? embeddedLogin ? 'Muse AI · Đăng nhập trong tool' : 'Muse AI · Trình duyệt ngoài (chế độ web)' : 'Muse AI · Adapter riêng'}</option><option value="demo">Kiểm thử giao diện · Không tạo video AI</option></select>
        <div className="connection-details"><Link2 size={18}/><div><strong>{connection}</strong><p>{settings.mode === 'muse' ? usingBrowser ? 'Cầu nối trình duyệt không chính thức. Đăng nhập một phiên Muse. Mặc định xử lý lần lượt; có thể chọn tối đa 10 luồng sau khi kiểm tra địa chỉ hội thoại riêng. Tool dùng lại hội thoại nếu Muse không có New chat và chỉ nhận ảnh/video trong lượt trả lời hiện tại. Mô hình/thời lượng là yêu cầu bằng lời, không bảo đảm Muse cung cấp đúng mọi thiết lập.' : 'Đang dùng adapter Muse riêng trong cấu hình máy chủ. Quyền tài khoản, mô hình và ảnh tham chiếu do adapter đó xử lý.' : 'Clip màu có nhãn TEST CLIP dùng để kiểm tra phát, tải và hàng đợi. Không đọc nội dung prompt, không thay cho video AI.'}</p></div></div>
        {renderBlocked && <div className="setup-help"><h3>Kết nối tài khoản để tạo ảnh/video</h3>{usingBrowser ? <><ol><li>{embeddedLogin ? 'Bấm Đăng nhập Muse trong tool; không cần cài Chrome riêng.' : 'Chạy start.bat để dùng bản desktop đăng nhập ngay trong tool. Chế độ web dùng Chrome/Edge ngoài.'}</li><li>Mở Tài khoản Muse, đăng nhập một lần cho cả 10 ô.</li><li>Đăng nhập Muse trong {loginPlace}. Quay lại Studio và bấm Kiểm tra phiên.</li><li>Khi phiên được xác minh, tạo thử một cảnh trước khi chạy hàng loạt.</li></ol><button className="button" onClick={() => setModal('accounts')}>Mở tài khoản Muse</button></> : <p>Chưa có adapter riêng. Để đăng nhập trực tiếp bằng trình duyệt, đặt MUSE_TRANSPORT=browser trong .env rồi khởi động lại máy chủ.</p>}<p className="small muted">Phiên lưu cục bộ trong hồ sơ riêng. Không gửi mật khẩu/cookie trong chat. Chế độ kiểm thử chỉ phát clip mẫu có nhãn.</p>{statusError && <pre>{statusError}</pre>}</div>}
        <div className="diagnostic-stats"><div><span>TRẠNG THÁI</span><b>{diagnosticBusy ? 'Đang kiểm tra…' : busy ? 'Đang có tác vụ' : 'Chờ kiểm tra'}</b></div><div><span>TOKEN / CREDIT</span><b>{balanceAccount?.balance ? `${balanceAccount.balance.valueText} ${balanceAccount.balance.unit}` : 'Chưa đọc được'}</b></div><div><span>GPU</span><b>Không được API cung cấp</b></div></div>
        <label className="checkbox-label consent"><input type="checkbox" checked={diagnosticConsent} disabled={locked} onChange={e => setDiagnosticConsent(e.target.checked)}/><span>{settings.mode === 'demo' ? 'Tôi muốn chạy clip kiểm thử giao diện.' : `Tôi đồng ý gửi một yêu cầu render thử (${settings.output === 'image' ? '1 ảnh 2K' : settings.model === 'Omni 1.1 Flash' ? '4s / 360p' : '8s / 360p'}), có thể tính phí theo tài khoản AI.`}</span></label>
        <div className="preset-row"><button className="button primary" disabled={!diagnosticConsent || locked || renderBlocked} onClick={() => void diagnose()}>{diagnosticBusy ? <LoaderCircle size={17} className="spin"/> : <Activity size={17}/>}Kiểm tra render thực tế</button><button className="button" disabled={locked || statusLoading} onClick={() => void refreshStatus()}><RefreshCw size={15}/>Đọc cấu hình</button>{diagnosticBusy && <button className="button danger" onClick={cancel}><Square size={15}/>Dừng chờ</button>}</div>
        {diagnostic && <div className={`diagnostic-result ${diagnostic.error ? 'failed' : ''}`} role="status"><p>{diagnostic.message}</p>{diagnostic.error && <pre>{diagnostic.error}</pre>}</div>}
        <div className="log-heading"><h3>Nhật ký lỗi gần nhất <span>{logs.length}</span></h3><button disabled={!logs.length} onClick={() => setLogs([])}><Trash2 size={13}/>Xóa nhật ký</button></div><div className="error-log">{logs.length ? logs.map((log, i) => <details key={i}><summary><span>{log.time}</span>{log.scene}<ChevronDown size={13}/></summary><p>{log.hint}</p><pre>{log.raw}</pre></details>) : <p className="muted">Chưa có lỗi được ghi nhận trong phiên này.</p>}</div>
      </div><footer className="modal-footer"><span className="small muted">Phiên Muse lưu trong hồ sơ riêng trên máy; không lưu trong dự án JSON.</span><button className="button" onClick={() => setModal(null)}>Đóng</button></footer>
    </Modal>}
  </div>;
}

createRoot(document.getElementById('root')!).render(<App/>);
