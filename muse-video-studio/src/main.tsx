import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Play, Download, FileText, Users, ShieldPlus, ImagePlus, ScanFace, WandSparkles, Clapperboard, X, Check, ChevronDown, RefreshCw, Square, Settings2, Activity, ArrowRight, Copy, Upload, CircleAlert, Video, Link2, Trash2, Film, FlaskConical, CheckCheck, LoaderCircle } from 'lucide-react';
import { ADVENTURE, RUNWAY, MUSE_MODELS, normalizeSettings, restoreWorkspace, parseScript, errorInfo, meetsResolution } from './core.ts';
import type { Scene, Settings, Reference, Status, Mode, Output, MediaResult } from './core.ts';
import { generateVideo, generateImage, enhancePrompt, readImage, downloadVideo, releaseVideo, providerStatus, accountAction } from './provider.ts';
import './styles.css';

const STORAGE = 'muse-workstation-v1';
const statusNames: Record<Status, string> = { ready: 'Sẵn sàng', queued: 'Đang chờ', running: 'Đang tạo', done: 'Hoàn tất', error: 'Lỗi', cancelled: 'Đã dừng' };
type Log = { time: string; scene: string; raw: string; hint: string };
type ModalName = 'import' | 'accounts' | 'diagnostics' | null;
type Balance = { valueText: string; unit: 'token' | 'credit'; label: string; observedAt: string; source: string };
type AccountSession = { balance?: Balance | null; id: number; state: string; authenticated: boolean; checkedAt: string | null; active: boolean };
type ProviderStatus = { museConfigured: boolean; busy: boolean; transport?: 'browser' | 'adapter'; accounts?: AccountSession[] };
const accountStateName = (account?: AccountSession) => !account ? 'Chưa kết nối' : account.authenticated ? account.active ? 'Đã xác minh' : 'Phiên đã lưu' : account.state === 'login_open' ? 'Chờ đăng nhập' : account.state === 'saved' ? 'Cần kiểm tra phiên' : 'Chưa kết nối';
function load() { try { return restoreWorkspace(localStorage.getItem(STORAGE)); } catch { return restoreWorkspace(null); } }
const initial = load();

function Modal({ title, eyebrow, children, close }: { title: string; eyebrow: string; children: React.ReactNode; close: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { const dialog = ref.current!; const previous = document.activeElement as HTMLElement;
    dialog.showModal(); return () => { dialog.close(); previous?.focus(); };
  }, []);
  return <dialog ref={ref} className="modal" onCancel={e => { e.preventDefault(); close(); }} onClick={e => { if (e.target === e.currentTarget) close(); }} aria-labelledby="modal-title">
    <header className="modal-head"><div><span className="eyebrow">{eyebrow}</span><h2 id="modal-title">{title}</h2></div><button className="icon-button" aria-label="Đóng" onClick={close}><X size={19}/></button></header>
    {children}
  </dialog>;
}

function App() {
  const [scenes, setScenes] = useState(initial.scenes);
  const scenesRef = useRef(scenes);
  const [settings, setSettings] = useState(initial.settings);
  const [globalImage, setGlobalImage] = useState<Reference | null>(null);
  const [modal, setModal] = useState<ModalName>(null);
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
  const [diagnosticBusy, setDiagnosticBusy] = useState(false);
  const [diagnostic, setDiagnostic] = useState<{ message: string; error?: string } | null>(null);
  const [diagnosticConsent, setDiagnosticConsent] = useState(false);
  const controller = useRef<AbortController | null>(null);
  const statusPending = useRef(false);
  const imageInput = useRef<HTMLInputElement>(null);
  const imageTarget = useRef<number | 'global'>('global');
  const fileInput = useRef<HTMLInputElement>(null);
  const locked = busy || diagnosticBusy || downloading || imageBusy || connectingId !== null;
  const done = scenes.filter(s => s[settings.output]).length;
  const outputLabel = settings.output === 'image' ? 'ảnh' : 'video';
  const enabled = scenes.filter(s => s.enabled).length;
  const parsed = parseScript(importText);
  const canImport = parsed.length > 0 && parsed.length <= 10;
  const usingBrowser = status?.transport === 'browser';
  const museAccount = status?.accounts?.find(account => account.id === 1);
  const balanceAccount = museAccount;
  const providerReady = settings.mode === 'demo' || Boolean(status?.museConfigured && (!usingBrowser || museAccount?.authenticated));
  const accountReady = () => providerReady;
  const sourceReady = (scene: Scene) => settings.output !== 'video' || settings.videoInput !== 'image' || Boolean(scene.reference || scene.image);
  const renderBlocked = !providerReady;
  const connectionProblem = statusLoading ? 'Đang đọc cấu hình kết nối từ máy chủ…' : statusError ? 'Không đọc được cấu hình máy chủ. Kiểm tra cửa sổ chạy tool rồi bấm Đọc cấu hình.' : usingBrowser ? 'Đăng nhập một tài khoản Muse trong cửa sổ Chrome/Edge rồi Kiểm tra phiên. Cả 10 ô sử dụng duy nhất phiên này.' : 'Chưa cấu hình adapter Muse riêng. Chọn kết nối trình duyệt trong cấu hình máy chủ để đăng nhập bằng Chrome/Edge.';

  async function refreshStatus(showLoading = true) {
    if (statusPending.current) return;
    statusPending.current = true;
    if (showLoading) setStatusLoading(true);
    setStatusError('');
    try { setStatus(await providerStatus()); }
    catch (e) { setStatus(null); setStatusError(errorInfo(e).raw); }
    finally { setStatusLoading(false); statusPending.current = false; }
  }
  function requireProvider() {
    if (providerReady) return true;
    setModal(usingBrowser ? 'accounts' : 'diagnostics'); setNotice(connectionProblem); return false;
  }
  async function connectAccount(check = false) {
    if (locked) return;
    setConnectingId(1);
    try {
      const result = await accountAction(check ? 'check' : 'connect');
      setStatus(current => current ? { ...current, accounts: result.accounts } : current);
      setNotice(result.accounts.some((account: AccountSession) => account.id === 1 && account.authenticated) ? 'Đã xác minh tài khoản Muse. Cả 10 ô đã dùng chung phiên này.' : 'Đăng nhập Muse trong cửa sổ Chrome/Edge được mở, rồi Kiểm tra phiên. Không nhập mật khẩu trong tool.');
    } catch (e) { setNotice(logError(e, 'Kết nối Muse').raw); }
    finally { setConnectingId(null); void refreshStatus(false); }
  }

  function updateScenes(fn: (current: Scene[]) => Scene[]) { const next = fn(scenesRef.current); scenesRef.current = next; setScenes(next); }
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
    setSettings(next);
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
    setSettings(current => ({ ...current, output: 'video', videoInput: 'image' }));
    setNotice('Đã dùng ảnh đã tạo làm đầu vào video. Prompt và ảnh được giữ nguyên.');
  }
  function logError(error: unknown, scene: string) {
    const info = errorInfo(error);
    setLogs(all => [{ ...info, scene, time: new Date().toLocaleTimeString('vi-VN') }, ...all].slice(0, 30));
    return info;
  }
  useEffect(() => { void refreshStatus(); }, []);
  useEffect(() => {
    if (!usingBrowser || busy || diagnosticBusy || connectingId !== null || !['accounts', 'diagnostics'].includes(modal || '')) return;
    const timer = setInterval(() => { void refreshStatus(false); }, 3000);
    return () => clearInterval(timer);
  }, [usingBrowser, modal, busy, diagnosticBusy, connectingId]);
  useEffect(() => {
    try { localStorage.setItem(STORAGE, JSON.stringify({ version: 1, settings, scenes: scenes.map(({ prompt, enabled }) => ({ prompt, enabled })) })); }
    catch { setNotice('Trình duyệt không lưu được phiên. Hãy xuất dự án JSON để giữ kịch bản.'); }
  }, [scenes, settings]);
  useEffect(() => { if (!notice) return; const timer = setTimeout(() => setNotice(''), 7000); return () => clearTimeout(timer); }, [notice]);
  useEffect(() => () => { controller.current?.abort(); scenesRef.current.forEach(s => { releaseVideo(s.video); releaseVideo(s.image); }); }, []);

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
  async function run(ids?: number[], override?: Scene[]) {
    if (controller.current || !requireProvider()) return;
    const source = override || scenesRef.current;
    const targets = source.filter(s => s.enabled && s.prompt.trim() && sourceReady(s) && accountReady() && (ids ? ids.includes(s.id) : !s[settings.output]));
    if (!targets.length) return setNotice('Không có cảnh cần tạo với tài khoản đã sẵn sàng.');
    const control = new AbortController(); controller.current = control;
    setBusy(true); setBatch(targets.length > 1); setCancelling(false);
    const queuedIds = new Set(targets.map(scene => scene.id));
    updateScenes(all => all.map(scene => queuedIds.has(scene.id) ? { ...scene, status: 'queued', error: undefined } : scene));
    setNotice(`Đã xếp ${targets.length} ${outputLabel} vào hàng đợi của một tài khoản Muse. Tool tự chạy lần lượt; không cần bấm từng ô.`);
    let completed = 0; let failed = 0;
    let loginRequired = false;
    try {
      for (const scene of targets) {
        if (control.signal.aborted) break;
        changeScene(scene.id, { status: 'running' }, true, settings.output);
        try {
          if (!scene.prompt.trim()) throw new Error('EMPTY_PROMPT: Cảnh chưa có prompt.');
          const reference = scene.reference || (settings.output === 'video' && settings.videoInput === 'image' && scene.image ? imageReference(scene.image, scene.id) : null);
          const generate = settings.output === 'image' ? generateImage : generateVideo;
          const media = await generate(scene.prompt, reference, settings, control.signal);
          if (control.signal.aborted) { releaseVideo(media); throw new DOMException('Đã dừng', 'AbortError'); }
          changeScene(scene.id, { status: 'done', ...(settings.output === 'image' ? { image: media } : { video: media }) }, false); completed++;
          await refreshStatus(false);
        } catch (e) {
          if (control.signal.aborted) { changeScene(scene.id, { status: 'cancelled' }, false); break; }
          const info = logError(e, `Cảnh #${String(scene.id).padStart(2, '0')}`);
          changeScene(scene.id, { status: 'error', error: info.raw }, false); failed++;
          if (/MUSE_LOGIN_REQUIRED/.test(info.raw)) { loginRequired = true; break; }
          if (/MUSE_NOT_CONFIGURED|MODEL_UNSUPPORTED/.test(info.raw)) break;
        }
      }
      setNotice(control.signal.aborted ? 'Đã dừng hàng đợi. Yêu cầu đã gửi có thể vẫn được tính phí.' : loginRequired ? 'Đã dừng bộ tạo vì phiên Muse cần đăng nhập lại. Kết nối lại rồi bấm một lần để tiếp tục các cảnh chưa xong.' : `Đã xử lý ${outputLabel}: ${completed} hoàn tất, ${failed} lỗi${settings.mode === 'demo' ? ' · Tệp kiểm thử, không phải AI.' : '.'}`);
    } finally {
      updateScenes(all => all.map(scene => scene.status === 'queued' ? { ...scene, status: scene[settings.output] ? 'done' : 'ready' } : scene));
      controller.current = null; setBusy(false); setBatch(false); setCancelling(false); void refreshStatus(false);
    }
  }
  async function enhance(scene: Scene) {
    if (controller.current || !scene.prompt.trim() || settings.mode === 'demo' || !requireProvider()) return;
    const control = new AbortController(); controller.current = control; setBusy(true);
    changeScene(scene.id, { enhancing: true }, false);
    try { const prompt = await enhancePrompt(scene.prompt, settings.mode, control.signal); changeScene(scene.id, { prompt }); }
    catch (e) { if (!control.signal.aborted) setNotice(logError(e, `Enhance #${scene.id}`).raw); }
    finally { changeScene(scene.id, { enhancing: false }, false); controller.current = null; setBusy(false); setCancelling(false); }
  }
  function cancel() { setCancelling(true); controller.current?.abort(); }
  async function downloadAll() {
    setDownloading(true);
    try { for (const scene of scenesRef.current) if (scene[settings.output]) { await downloadVideo(scene[settings.output]!, scene.id); await new Promise(r => setTimeout(r, 250)); }
      setNotice('Đã gửi các lệnh tải. Nếu trình duyệt hỏi, cho phép tải nhiều tệp.');
    } catch (e) { setNotice(logError(e, 'Tải video').raw); }
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
    if (controller.current || !diagnosticConsent || !requireProvider()) return;
    setDiagnosticBusy(true); setDiagnostic(null);
    const control = new AbortController(); controller.current = control;
    const started = performance.now();
    try {
      const testSettings = normalizeSettings({ ...settings, duration: 4, resolution: '360p', imageResolution: '2k', videoInput: 'text', modifier: '', r2v: false });
      const generate = settings.output === 'image' ? generateImage : generateVideo;
      const video = await generate('A calm ocean at sunrise, gentle waves, cinematic composition.', null, testSettings, control.signal);
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
      const restored = restoreWorkspace(text); updateScenes(all => { all.forEach(s => { releaseVideo(s.video); releaseVideo(s.image); }); return restored.scenes; }); setSettings(restored.settings); setGlobalImage(null); setNotice('Đã mở dự án. Chọn lại ảnh tham chiếu; video và ảnh không lưu trong JSON.');
    } catch (e) { setNotice(errorInfo(e).raw); }
  }
  const connection = settings.mode === 'demo' ? 'Kiểm thử · không dùng AI' : usingBrowser ? (museAccount?.authenticated ? 'Muse · Đã xác minh' : 'Muse · Chưa đăng nhập') : status?.museConfigured ? 'Đã khai báo adapter Muse' : 'Chưa kết nối Muse AI';

  return <div className="app-shell">
    <input ref={imageInput} type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={e => { void handleImage(e.target.files?.[0]); e.target.value = ''; }}/>
    <input ref={fileInput} type="file" accept=".txt,.srt" hidden onChange={e => { void importFile(e.target.files?.[0]); e.target.value = ''; }}/>
    <header className="topbar">
      <div className="studio-tabs" aria-label="Loại nội dung"><button disabled={locked} aria-pressed={settings.output === 'video'} onClick={() => changeSettings({ output: 'video' })}><Video size={17}/>Tạo video</button><button disabled={locked} aria-pressed={settings.output === 'image'} onClick={() => changeSettings({ output: 'image' })}><ImagePlus size={17}/>Tạo ảnh hàng loạt</button><span>MUSE AI STUDIO · ẢNH / VIDEO</span></div>
      <div className="actions-row">
        {busy ? <button className="button danger" onClick={cancel} disabled={cancelling}><Square size={16}/>{cancelling ? 'Đang dừng…' : batch ? 'Dừng hàng đợi' : 'Dừng tác vụ'}</button> : <button className="button primary" title={renderBlocked ? connectionProblem : 'Tạo lần lượt các cảnh đang bật'} disabled={locked || !enabled || renderBlocked || !scenes.some(s => s.enabled && accountReady() && sourceReady(s))} onClick={() => void run()}><Play size={17} fill="currentColor"/>TẠO 10 {outputLabel.toLocaleUpperCase('vi')}</button>}
        <button className="button" disabled={!done || downloading || locked} onClick={() => void downloadAll()}><Download size={17}/>{downloading ? 'Đang tải…' : `Tải tất cả (${done}/10)`}</button>
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
      <section className="single-account-panel" aria-label="Một tài khoản Muse và số dư">
        <div><span className="eyebrow">MỘT TÀI KHOẢN DUY NHẤT</span><h2>Đăng nhập một lần · Tạo cả bộ 10 cảnh</h2><p>Nhập đủ 10 prompt hoặc TXT/SRT, chọn ảnh/video rồi bấm Tạo 10 một lần. Tool tự chạy lần lượt trên cùng phiên Muse.</p></div>
        <div className="single-account-controls"><strong className={providerReady ? 'mint' : 'muted'}>{usingBrowser ? accountStateName(museAccount) : connection}</strong><button className="button" disabled={locked || !usingBrowser} onClick={() => void connectAccount()}><Link2 size={15}/>{connectingId !== null ? 'Đang kết nối…' : 'Kết nối Muse'}</button><button className="micro-button" disabled={locked || !usingBrowser} onClick={() => void connectAccount(true)}>Kiểm tra phiên</button></div>
        <div className="balance-card" data-testid="account-balance"><span>SỐ DƯ TÀI KHOẢN MUSE</span><strong>{settings.mode === 'demo' ? 'Chế độ kiểm thử' : balanceAccount?.balance ? `${balanceAccount.balance.valueText} ${balanceAccount.balance.unit}` : 'Chưa đọc được'}</strong><small>{balanceAccount?.balance ? `Đọc lúc ${new Date(balanceAccount.balance.observedAt).toLocaleTimeString('vi-VN')}` : 'Không tự suy đoán token hoặc credit'}</small><button className="micro-button" disabled={locked || !usingBrowser || !museAccount?.authenticated} onClick={() => void connectAccount(true)}><RefreshCw size={12}/>Cập nhật số dư</button></div>
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
        <div className="progress-box"><span>Tiến độ tạo:</span><div className="progress-track" role="progressbar" aria-label="Tiến độ tạo" aria-valuemin={0} aria-valuemax={10} aria-valuenow={done}><div style={{ width: `${done * 10}%` }}/></div><b>{done}/10</b></div>
      </section>

      {settings.output === 'image' && scenes.some(s => s.image) && <div className="image-batch-actions"><button className="button" disabled={locked} onClick={() => useImagesForVideo()}><Video size={16}/>Chuyển bộ ảnh đã tạo sang video</button><span>Giữ ảnh và prompt, dùng ảnh đã tạo làm khung hình đầu.</span></div>}
      <section className="scene-grid" aria-label="10 phân cảnh ảnh và video">{scenes.map(scene => {
        const media = scene[settings.output];
        const needsSource = settings.output === 'video' && settings.videoInput === 'image' && !scene.reference && !scene.image;
        const quality = media ? meetsResolution(media) : null;
        return <article key={scene.id} className={`scene-card ${!scene.enabled ? 'disabled-card' : ''} status-${scene.status}`} data-testid={`scene-${scene.id}`}>
          <header className="scene-header"><span className="scene-number">#{String(scene.id).padStart(2, '0')}</span><span className={`status-badge ${scene.status}`}>{scene.status === 'running' && <LoaderCircle className="spin" size={10}/>}{statusNames[scene.status]}</span><label className="scene-enable"><input type="checkbox" aria-label={`Bật cảnh ${scene.id}`} checked={scene.enabled} disabled={locked} onChange={e => changeScene(scene.id, { enabled: e.target.checked }, false)}/>Bật</label><span className="same-account-tag">Muse</span></header>
          <div className="card-content">
            <div className="video-preview">{media ? <>{media.kind === 'image' ? <a href={media.url} target="_blank" rel="noopener noreferrer" aria-label={`Xem ảnh cảnh ${scene.id}`}><img className="generated-image" src={media.url} alt={`Ảnh kết quả cảnh ${scene.id}`}/></a> : <video src={media.url} controls playsInline preload="metadata" aria-label={`Video cảnh ${scene.id}`}/>} {media.demo && <span className="preview-label">{media.kind === 'image' ? 'ẢNH KIỂM THỬ' : 'CLIP KIỂM THỬ'}</span>}</> : <div className="empty-video">{scene.status === 'running' ? <LoaderCircle className="spin" size={25}/> : settings.output === 'image' ? <ImagePlus size={23}/> : <Clapperboard size={23}/>}<span>{scene.status === 'running' ? `Đang tạo ${outputLabel}…` : scene.status === 'queued' ? 'Đang chờ đến lượt…' : scene.status === 'error' ? `Tạo ${outputLabel} thất bại` : !scene.enabled ? 'Cảnh đã tắt' : `Chưa khởi tạo ${outputLabel}`}</span>{scene.status === 'running' && <small>Có thể mất vài phút</small>}</div>}</div>
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
            <div className="prompt-label"><label htmlFor={`prompt-${scene.id}`}>Kịch bản Prompt:</label><button disabled={locked || !accountReady() || settings.mode === 'demo' || !scene.prompt.trim() || !scene.enabled} onClick={() => void enhance(scene)} title="Dịch và trau chuốt prompt bằng AI">{scene.enhancing ? <LoaderCircle size={18} className="spin"/> : <WandSparkles size={19}/>}AI Enhance</button></div>
            <textarea id={`prompt-${scene.id}`} aria-label={`Kịch bản cảnh ${scene.id}`} disabled={locked} maxLength={8000} value={scene.prompt} onChange={e => changeScene(scene.id, { prompt: e.target.value })} placeholder="Nhập mô tả phân cảnh…"/>
            {scene.error && <div className="scene-error"><span><CircleAlert size={13}/>{errorInfo(scene.error).hint}</span><details><summary>Mã lỗi gốc</summary><pre>{scene.error}</pre></details></div>}
          </div>
          <footer className="card-footer"><button className={`scene-run ${media ? 'has-result' : ''}`} disabled={locked || !accountReady() || !scene.enabled || !scene.prompt.trim() || needsSource} onClick={() => void run([scene.id])}>{media || scene.status === 'error' ? <RefreshCw size={15}/> : <Play size={15}/>} {media ? 'Tạo lại cảnh' : scene.status === 'error' ? 'Thử lại cảnh này' : 'Tạo cảnh này'}</button>{media && <button className="download-one" title={`Tải cảnh ${scene.id}`} aria-label={`Tải cảnh ${scene.id}`} onClick={() => void downloadVideo(media, scene.id).catch(e => setNotice(logError(e, 'Tải tệp').raw))}><Download size={16}/></button>}</footer>
        </article>;
      })}</section>
      <footer className="workspace-footer"><span><i/>Tự lưu kịch bản trên trình duyệt <span className="footer-divider">/</span> Ảnh & video chỉ giữ trong phiên</span><div><label className={`footer-button ${locked ? 'muted' : ''}`}><Upload size={13}/>Mở dự án<input type="file" accept=".json" hidden disabled={locked} onChange={e => { void restoreProject(e.target.files?.[0]); e.target.value = ''; }}/></label><button onClick={exportProject}><Download size={13}/>Xuất dự án JSON</button></div></footer>
    </main>
    {notice && <div className="toast" role="status"><CircleAlert size={17}/><span>{notice}</span><button aria-label="Đóng thông báo" onClick={() => setNotice('')}><X size={15}/></button></div>}

    {modal === 'import' && <Modal title="Nhập kịch bản thông minh" eyebrow="SCRIPT IMPORT / 10 SCENES" close={() => setModal(null)}>
      <div className="modal-body"><p className="muted">TXT: mỗi dòng hoặc mỗi đoạn là một cảnh. SRT: mỗi khối phụ đề là một cảnh, tự bỏ số thứ tự và timestamp. Tối đa 10 cảnh.</p><div className="preset-row"><button className="button" onClick={() => setImportText(ADVENTURE.join('\n\n'))}><Film size={16}/>Điện ảnh phiêu lưu</button><button className="button" onClick={() => setImportText(RUNWAY.join('\n\n'))}><WandSparkles size={16}/>Thời trang Runway</button><button className="button" onClick={() => fileInput.current?.click()}><Upload size={16}/>Chọn TXT / SRT</button></div>
        <textarea className="import-text" aria-label="Nội dung TXT / SRT" value={importText} onChange={e => setImportText(e.target.value)} placeholder={'Dán kịch bản hoặc phụ đề vào đây…\n\n1\n00:00:00,000 --> 00:00:04,000\nMột người thám hiểm bước vào ngôi đền cổ.'}/>
        <div className="import-count"><b className={parsed.length > 10 ? 'red' : 'mint'}>{parsed.length}/10 cảnh</b><span>{parsed.length > 10 ? 'Có hơn 10 cảnh. Rút gọn trước khi nạp, không tự cắt bỏ nội dung.' : parsed.length < 10 ? 'Các ô còn lại sẽ được để trống.' : 'Đã đủ 10 phân cảnh.'}</span></div>
        <div className="script-preview">{parsed.slice(0, 10).map((text, i) => <div key={i}><span>#{String(i + 1).padStart(2, '0')}</span><p>{text}</p></div>)}</div><p className="small muted">Nạp kịch bản sẽ thay prompt và xóa kết quả ảnh/video cũ của 10 cảnh. Giữ ảnh tham chiếu và tài khoản.</p>
      </div><footer className="modal-footer"><button className="button" onClick={() => setModal(null)}>Đóng</button><button className="button" disabled={!canImport || locked} onClick={() => importScenes(false)}>Nạp vào Studio</button><button className="button primary" disabled={!canImport || locked || renderBlocked} onClick={() => importScenes(true)}><Play size={15}/>Nạp & Chạy các cảnh</button></footer>
    </Modal>}

    {modal === 'accounts' && <Modal title="Tài khoản Muse duy nhất" eyebrow="ONE ACCOUNT / 10 SCENES" close={() => setModal(null)}>
      <div className="modal-body"><div className="info-note"><Users size={18}/><span>Chỉ đăng nhập một tài khoản Muse. Cả 10 ô ảnh/video tự dùng cùng phiên đó; bấm Tạo 10 một lần để chạy cả bộ. Không cần email, gán tài khoản hoặc kết nối thêm hồ sơ.</span></div>
        <div className="single-account-dialog"><strong className={providerReady ? 'mint' : 'muted'}>{usingBrowser ? accountStateName(museAccount) : connection}</strong><p className="muted">Đăng nhập trong cửa sổ Chrome/Edge được tool mở rồi Kiểm tra phiên. Hạn mức và tốc độ tạo phụ thuộc tài khoản Muse này.</p>{usingBrowser && <div className="preset-row"><button className="button primary" disabled={locked} onClick={() => void connectAccount()}><Link2 size={16}/>Mở cửa sổ Muse</button><button className="button" disabled={locked} onClick={() => void connectAccount(true)}>Kiểm tra phiên Muse</button></div>}</div>
        <label className="field-label" htmlFor="global-modifier">Chỉ thị chất lượng toàn cục <span className="tag">GLOBAL PROMPT MODIFIER</span></label><textarea id="global-modifier" className="bulk-text" disabled={locked} maxLength={2000} value={settings.modifier} onChange={e => changeSettings({ modifier: e.target.value })} placeholder="cinematic lighting, photorealistic, professional 35mm lens…"/><p className="small muted">Nối vào cuối mọi prompt tạo ảnh/video. Thay đổi chỉ thị sẽ xóa kết quả cũ để tránh dùng video không còn khớp kịch bản.</p>
      </div><footer className="modal-footer"><span className="small muted">{enabled}/10 cảnh đang bật · Tự lưu</span><button className="button primary" onClick={() => setModal(null)}><Check size={16}/>Hoàn tất</button></footer>
    </Modal>}

    {modal === 'diagnostics' && <Modal title="Chẩn đoán & kết nối API" eyebrow="CONNECTION / HEALTH / ERROR LOG" close={() => setModal(null)}>
      <div className="modal-body"><label className="field-label" htmlFor="provider-mode">Kết nối tạo video</label><select id="provider-mode" className="provider-select" disabled={locked} value={settings.mode} onChange={e => { const mode = e.target.value as Mode; changeSettings({ mode }); setDiagnostic(null); setDiagnosticConsent(false); }}><option value="muse">{usingBrowser ? 'Muse AI · Tài khoản Chrome/Edge' : 'Muse AI · Adapter riêng'}</option><option value="demo">Kiểm thử giao diện · Không tạo video AI</option></select>
        <div className="connection-details"><Link2 size={18}/><div><strong>{connection}</strong><p>{settings.mode === 'muse' ? usingBrowser ? 'Cầu nối trình duyệt không chính thức. Đăng nhập bằng nút Kết nối ở Tài khoản Muse. Tool gửi prompt và ảnh trong phiên đó, chỉ nhận ảnh/video mới trả về. Mô hình/thời lượng là yêu cầu bằng lời, không bảo đảm Muse cung cấp đúng mọi thiết lập.' : 'Đang dùng adapter Muse riêng trong cấu hình máy chủ. Quyền tài khoản, mô hình và ảnh tham chiếu do adapter đó xử lý.' : 'Clip màu có nhãn TEST CLIP dùng để kiểm tra phát, tải và hàng đợi. Không đọc nội dung prompt, không thay cho video AI.'}</p></div></div>
        {renderBlocked && <div className="setup-help"><h3>Kết nối tài khoản để tạo ảnh/video</h3>{usingBrowser ? <><ol><li>Cài Chrome hoặc Edge trên máy chạy tool.</li><li>Mở Tài khoản Muse, đăng nhập một lần cho cả 10 ô.</li><li>Đăng nhập Muse trong cửa sổ được mở. Quay lại tool và bấm Kiểm tra phiên.</li><li>Khi phiên được xác minh, tạo thử một cảnh trước khi chạy hàng loạt.</li></ol><button className="button" onClick={() => setModal('accounts')}>Mở tài khoản Muse</button></> : <p>Chưa có adapter riêng. Để đăng nhập trực tiếp bằng trình duyệt, đặt MUSE_TRANSPORT=browser trong .env rồi khởi động lại máy chủ.</p>}<p className="small muted">Phiên lưu cục bộ trong hồ sơ riêng. Không gửi mật khẩu/cookie trong chat. Chế độ kiểm thử chỉ phát clip mẫu có nhãn.</p>{statusError && <pre>{statusError}</pre>}</div>}
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
