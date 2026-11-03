import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Play, Download, FileText, Users, ShieldPlus, ImagePlus, ScanFace, WandSparkles, Clapperboard, X, Check, ChevronDown, RefreshCw, Square, Settings2, Activity, ArrowRight, Copy, Upload, CircleAlert, Video, Link2, Trash2, Film, FlaskConical, CheckCheck, LoaderCircle } from 'lucide-react';
import { ADVENTURE, RUNWAY, MUSE_MODELS, normalizeSettings, restoreWorkspace, parseScript, extractEmails, errorInfo } from './core.ts';
import type { Scene, Settings, Reference, Status, Mode } from './core.ts';
import { generateVideo, enhancePrompt, readImage, downloadVideo, releaseVideo, providerStatus } from './provider.ts';
import './styles.css';

const STORAGE = 'muse-workstation-v1';
const statusNames: Record<Status, string> = { ready: 'Sẵn sàng', running: 'Đang tạo', done: 'Hoàn tất', error: 'Lỗi', cancelled: 'Đã dừng' };
type Log = { time: string; scene: string; raw: string; hint: string };
type ModalName = 'import' | 'accounts' | 'diagnostics' | null;
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
  const [emailText, setEmailText] = useState('');
  const [status, setStatus] = useState<{ museConfigured: boolean; busy: boolean } | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [statusError, setStatusError] = useState('');
  const [diagnosticBusy, setDiagnosticBusy] = useState(false);
  const [diagnostic, setDiagnostic] = useState<{ message: string; error?: string } | null>(null);
  const [diagnosticConsent, setDiagnosticConsent] = useState(false);
  const controller = useRef<AbortController | null>(null);
  const imageInput = useRef<HTMLInputElement>(null);
  const imageTarget = useRef<number | 'global'>('global');
  const fileInput = useRef<HTMLInputElement>(null);
  const locked = busy || diagnosticBusy || downloading || imageBusy;
  const done = scenes.filter(s => s.video && s.status === 'done').length;
  const enabled = scenes.filter(s => s.enabled).length;
  const parsed = parseScript(importText);
  const canImport = parsed.length > 0 && parsed.length <= 10;
  const providerReady = settings.mode === 'demo' || status?.museConfigured === true;
  const renderBlocked = !providerReady;
  const connectionProblem = statusLoading ? 'Đang đọc cấu hình kết nối từ máy chủ…' : statusError ? 'Không đọc được cấu hình máy chủ. Kiểm tra cửa sổ chạy tool rồi bấm Đọc cấu hình.' : 'Chưa có kết nối tạo video AI của Muse. Cần xác thực tài khoản qua API được Muse hỗ trợ; chỉ nhập email chưa đủ để kết nối.';

  async function refreshStatus() {
    setStatusLoading(true); setStatusError('');
    try { setStatus(await providerStatus()); }
    catch (e) { setStatus(null); setStatusError(errorInfo(e).raw); }
    finally { setStatusLoading(false); }
  }
  function requireProvider() {
    if (providerReady) return true;
    setModal('diagnostics'); setNotice(connectionProblem); return false;
  }

  function updateScenes(fn: (current: Scene[]) => Scene[]) { const next = fn(scenesRef.current); scenesRef.current = next; setScenes(next); }
  function invalidate(scene: Scene): Scene { releaseVideo(scene.video); return { ...scene, video: undefined, status: 'ready', error: undefined }; }
  function changeScene(id: number, patch: Partial<Scene>, reset = true) { updateScenes(all => all.map(s => s.id === id ? { ...(reset ? invalidate(s) : s), ...patch } : s)); }
  function changeSettings(patch: Partial<Settings>, reset = true) {
    if (locked) return;
    setSettings(s => normalizeSettings({ ...s, ...patch }));
    if (reset) updateScenes(all => all.map(invalidate));
  }
  function logError(error: unknown, scene: string) {
    const info = errorInfo(error);
    setLogs(all => [{ ...info, scene, time: new Date().toLocaleTimeString('vi-VN') }, ...all].slice(0, 30));
    return info;
  }
  useEffect(() => { void refreshStatus(); }, []);
  useEffect(() => {
    try { localStorage.setItem(STORAGE, JSON.stringify({ version: 1, settings, scenes: scenes.map(({ prompt, email, enabled }) => ({ prompt, email, enabled })) })); }
    catch { setNotice('Trình duyệt không lưu được phiên. Hãy xuất dự án JSON để giữ kịch bản.'); }
  }, [scenes, settings]);
  useEffect(() => { if (!notice) return; const timer = setTimeout(() => setNotice(''), 7000); return () => clearTimeout(timer); }, [notice]);
  useEffect(() => () => { controller.current?.abort(); scenesRef.current.forEach(s => releaseVideo(s.video)); }, []);

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
    const targets = source.filter(s => s.enabled && (ids ? ids.includes(s.id) : s.status !== 'done'));
    if (!targets.length) return setNotice('Không có cảnh cần tạo. Bật tài khoản hoặc chỉnh kịch bản để tạo lại.');
    const control = new AbortController(); controller.current = control;
    setBusy(true); setBatch(targets.length > 1); setCancelling(false);
    let completed = 0;
    let failed = 0;
    try {
      for (const scene of targets) {
        if (control.signal.aborted) break;
        changeScene(scene.id, { status: 'running' });
        try {
          if (!scene.prompt.trim()) throw new Error('EMPTY_PROMPT: Cảnh chưa có kịch bản.');
          const video = await generateVideo(scene.prompt, scene.reference, settings, control.signal, scene.id);
          if (control.signal.aborted) { releaseVideo(video); throw new DOMException('Đã dừng', 'AbortError'); }
          changeScene(scene.id, { status: 'done', video }, false); completed++;
        } catch (e) {
          if (control.signal.aborted) { changeScene(scene.id, { status: 'cancelled' }, false); break; }
          const info = logError(e, `Cảnh #${String(scene.id).padStart(2, '0')}`);
          changeScene(scene.id, { status: 'error', error: info.raw }, false); failed++;
          // Avoid ten identical failing requests when the provider is absent.
          if (/MUSE_NOT_CONFIGURED|MODEL_UNSUPPORTED/.test(info.raw)) break;
        }
      }
      setNotice(control.signal.aborted ? 'Đã dừng hàng đợi. Yêu cầu AI đã gửi có thể vẫn được tính phí.' : `Đã xử lý: ${completed} hoàn tất, ${failed} lỗi${settings.mode === 'demo' ? ' · Clip kiểm thử, không phải video AI.' : '.'}`);
    } finally { controller.current = null; setBusy(false); setBatch(false); setCancelling(false); }
  }
  async function enhance(scene: Scene) {
    if (controller.current || !scene.prompt.trim() || settings.mode === 'demo' || !requireProvider()) return;
    const control = new AbortController(); controller.current = control; setBusy(true);
    changeScene(scene.id, { enhancing: true }, false);
    try { const prompt = await enhancePrompt(scene.prompt, settings.mode, control.signal, scene.id); changeScene(scene.id, { prompt }); }
    catch (e) { if (!control.signal.aborted) setNotice(logError(e, `Enhance #${scene.id}`).raw); }
    finally { changeScene(scene.id, { enhancing: false }, false); controller.current = null; setBusy(false); setCancelling(false); }
  }
  function cancel() { setCancelling(true); controller.current?.abort(); }
  async function downloadAll() {
    setDownloading(true);
    try { for (const scene of scenesRef.current) if (scene.video) { await downloadVideo(scene.video, scene.id); await new Promise(r => setTimeout(r, 250)); }
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
      const testSettings = normalizeSettings({ ...settings, duration: 4, resolution: '360p', modifier: '', r2v: false });
      const video = await generateVideo('A calm ocean at sunrise, gentle waves, slow cinematic camera movement.', null, testSettings, control.signal, 1);
      releaseVideo(video);
      setDiagnostic({ message: `${settings.mode === 'demo' ? 'Luồng kiểm thử' : 'Render thử'} hoàn tất sau ${((performance.now() - started) / 1000).toFixed(1)} giây. ${testSettings.duration}s · ${testSettings.resolution}. Credit và GPU: API không cung cấp thông tin.` });
    } catch (e) { const info = logError(e, 'Chẩn đoán'); setDiagnostic({ message: info.hint, error: info.raw }); }
    finally { controller.current = null; setDiagnosticBusy(false); setCancelling(false); void refreshStatus(); }
  }
  function exportProject() {
    const blob = new Blob([JSON.stringify({ version: 1, settings, scenes: scenes.map(({ prompt, email, enabled }) => ({ prompt, email, enabled })) }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'muse-studio-project.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  async function restoreProject(file?: File) {
    if (!file || locked) return;
    if (file.size > 2 * 1024 * 1024) return setNotice('Dự án tối đa 2 MB.');
    try { const text = await file.text(); const value = JSON.parse(text);
      if (value.version !== 1 || !Array.isArray(value.scenes) || value.scenes.length !== 10) throw new Error('Dự án không đúng định dạng Muse Studio v1 (10 cảnh).');
      const restored = restoreWorkspace(text); updateScenes(all => { all.forEach(s => releaseVideo(s.video)); return restored.scenes; }); setSettings(restored.settings); setGlobalImage(null); setNotice('Đã mở dự án. Chọn lại ảnh tham chiếu; video và ảnh không lưu trong JSON.');
    } catch (e) { setNotice(errorInfo(e).raw); }
  }
  const connection = settings.mode === 'demo' ? 'Kiểm thử · không dùng AI' : status?.museConfigured ? 'Đã khai báo Muse AI' : 'Chưa kết nối Muse AI';

  return <div className="app-shell">
    <input ref={imageInput} type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={e => { void handleImage(e.target.files?.[0]); e.target.value = ''; }}/>
    <input ref={fileInput} type="file" accept=".txt,.srt" hidden onChange={e => { void importFile(e.target.files?.[0]); e.target.value = ''; }}/>
    <header className="topbar">
      <div className="actions-row">
        {busy ? <button className="button danger" onClick={cancel} disabled={cancelling}><Square size={16}/>{cancelling ? 'Đang dừng…' : batch ? 'Dừng hàng đợi' : 'Dừng tác vụ'}</button> : <button className="button primary" title={renderBlocked ? connectionProblem : 'Tạo lần lượt các cảnh đang bật'} disabled={locked || !enabled || renderBlocked} onClick={() => void run()}><Play size={17} fill="currentColor"/>CHẠY TOÀN BỘ 10 VIDEO</button>}
        <button className="button" disabled={!done || downloading || locked} onClick={() => void downloadAll()}><Download size={17}/>{downloading ? 'Đang tải…' : `Tải tất cả (${done}/10)`}</button>
        <button className="button" disabled={locked} onClick={() => setModal('import')}><FileText size={18}/>Nhập TXT / SRT</button>
        <button className="button" onClick={() => setModal('accounts')}><Users size={19}/>10 Tài khoản Muse</button>
        <button className="button diagnostic-button" onClick={() => setModal('diagnostics')}><ShieldPlus size={19}/>Chẩn đoán API</button>
        <span className={`connection-pill ${settings.mode === 'demo' ? 'is-demo' : status?.museConfigured ? 'connected' : ''}`} title="Mở Chẩn đoán API để cấu hình kết nối"><i/>{connection}</span>
      </div>
      <div className="settings-row">
        <label className="setting model-setting"><span>MODEL:</span><select aria-label="Model AI" disabled={locked} value={settings.model} onChange={e => changeSettings({ model: e.target.value as Settings['model'] })}>{MUSE_MODELS.map(model => <option key={model} value={model}>{model}{model === 'Omni 1.1 Flash' ? ' (Khuyên dùng)' : ''}</option>)}</select></label>
        <div className="setting"><span>KHUNG:</span><div className="segmented">{(['16:9', '9:16'] as const).map(ratio => <button key={ratio} disabled={locked} aria-pressed={settings.aspectRatio === ratio} onClick={() => changeSettings({ aspectRatio: ratio })}>{ratio}</button>)}</div></div>
        <label className="setting"><span>THỜI LƯỢNG:</span><select aria-label="Thời lượng" value={settings.duration} disabled={locked || settings.model !== 'Omni 1.1 Flash'} onChange={e => changeSettings({ duration: Number(e.target.value) })}>{[4, 6, 8, 10].map(n => <option key={n} value={n}>{n} giây</option>)}</select></label>
        <label className="setting"><span>CHẤT LƯỢNG:</span><select aria-label="Chất lượng" value={settings.resolution} disabled={locked || settings.model !== 'Omni 1.1 Flash'} onChange={e => changeSettings({ resolution: e.target.value as Settings['resolution'] })}><option value="360p">360p (Siêu tốc)</option><option value="720p">720p (HD)</option></select></label>
        <div className="setting sync-setting"><label className="checkbox-label"><input type="checkbox" checked={settings.r2v} disabled={locked} onChange={e => changeSettings({ r2v: e.target.checked })}/>Đồng bộ NV (R2V)</label><button className="micro-button" disabled={locked} onClick={() => void chooseImage('global')}>+ Chọn ảnh</button></div>
      </div>
    </header>

    <main>
      {renderBlocked && <section className="connection-warning" aria-label="Cần kết nối tạo video"><CircleAlert size={20}/><div><strong>{settings.mode === 'muse' && statusLoading ? 'Đang kiểm tra kết nối' : 'Chưa thể tạo video AI'}</strong><p>{connectionProblem}</p><p>Kịch bản và ảnh vẫn có thể chỉnh sửa. Tạo video và AI Enhance sẽ bật sau khi có kết nối phù hợp.</p></div><button className="button" onClick={() => setModal('diagnostics')}>Xem cách kết nối</button></section>}
      {settings.mode === 'demo' && <div className="demo-banner"><FlaskConical size={16}/>CHẾ ĐỘ KIỂM THỬ · Mỗi cảnh dùng cùng clip thử 4s/360p. Không tạo video AI từ kịch bản hoặc ảnh.</div>}
      <section className="character-banner" aria-label="Đồng nhất nhân vật">
        <button className={`global-image ${globalImage ? 'has-image' : ''}`} disabled={locked} onClick={() => void chooseImage('global')} aria-label={globalImage ? 'Đổi ảnh nhân vật chung' : 'Tải ảnh nhân vật chung'}>
          {globalImage?.url ? <img src={globalImage.url} alt="Ảnh nhân vật chung"/> : <><ImagePlus size={22}/><span>{globalImage ? 'Đổi ảnh' : 'Tải ảnh NV'}</span></>}
        </button>
        <div className="character-copy"><h1><ScanFace size={22}/>Ô NHẬP ẢNH ĐỒNG NHẤT NHÂN VẬT (10 TÀI KHOẢN / 10 SLOT) <span className="tag">R2V Reference</span></h1><p>{globalImage ? globalImage.name : 'Bấm vào ô để chọn ảnh chân dung nhân vật từ thư viện. Hệ thống sẽ tự động gán vào cả 10 tài khoản Muse.'}</p>{globalImage && <div className="image-actions"><button disabled={locked} onClick={() => void chooseImage('global')}>Đổi ảnh khác</button><button disabled={locked} onClick={() => { const old = globalImage; setGlobalImage(null); updateScenes(all => all.map(s => s.reference?.id === old.id ? { ...invalidate(s), reference: null } : s)); }}>Gỡ ảnh chung</button></div>}</div>
        <label className="auto-sync"><input type="checkbox" disabled={locked} checked={settings.autoSync} onChange={e => { changeSettings({ autoSync: e.target.checked }, false); if (e.target.checked && globalImage) updateScenes(all => all.map(s => ({ ...invalidate(s), reference: globalImage }))); }}/><span><b>Bật đồng nhất tự động</b><small>{settings.autoSync ? 'Đang bật R2V khung' : 'Gán ảnh thủ công'}</small></span></label>
        <button className="button apply-all" disabled={locked || !globalImage} onClick={() => { updateScenes(all => all.map(s => ({ ...invalidate(s), reference: globalImage }))); setNotice('Đã áp dụng ảnh chung cho cả 10 cảnh.'); }}><Users size={18}/>Áp dụng cho toàn bộ 10 tài khoản</button>
      </section>

      <section className="workstation-heading">
        <div className="studio-icon"><Video size={23}/></div><div className="heading-copy"><h2>10-SLOT VIDEO WORKSTATION <span className="tag">MUSE STUDIO ENGINE</span></h2><p>Điều phối 10 phân cảnh · Model: <span>{settings.model}</span> · Hỗ trợ ảnh tham chiếu nhân vật đồng nhất qua R2V.</p></div>
        <div className="progress-box"><span>Tiến độ tạo:</span><div className="progress-track" role="progressbar" aria-label="Tiến độ tạo" aria-valuemin={0} aria-valuemax={10} aria-valuenow={done}><div style={{ width: `${done * 10}%` }}/></div><b>{done}/10</b></div>
      </section>

      <section className="scene-grid" aria-label="10 phân cảnh video">{scenes.map(scene => <article key={scene.id} className={`scene-card ${!scene.enabled ? 'disabled-card' : ''} status-${scene.status}`} data-testid={`scene-${scene.id}`}>
        <header className="scene-header"><span className="scene-number">#{String(scene.id).padStart(2, '0')}</span><span className={`status-badge ${scene.status}`}>{scene.status === 'running' && <LoaderCircle className="spin" size={10}/>}{statusNames[scene.status]}</span><label className="account-inline"><Users size={17}/><input aria-label={`Tài khoản cảnh ${scene.id}`} type="email" disabled={locked} maxLength={120} value={scene.email} onChange={e => changeScene(scene.id, { email: e.target.value }, false)}/></label></header>
        <div className="card-content">
          <div className="video-preview">
            {scene.video ? <><video src={scene.video.url} controls playsInline preload="metadata" aria-label={`Video cảnh ${scene.id}`}/>{scene.video.demo && <span className="preview-label">CLIP KIỂM THỬ</span>}</> : <div className="empty-video">{scene.status === 'running' ? <LoaderCircle className="spin" size={25}/> : <Clapperboard size={23}/>}<span>{scene.status === 'running' ? 'Đang tạo video…' : scene.status === 'error' ? 'Tạo video thất bại' : !scene.enabled ? 'Tài khoản đã tắt' : 'Chưa khởi tạo video'}</span>{scene.status === 'running' && <small>Có thể mất vài phút</small>}</div>}
          </div>
          <div className="reference-box"><div className="reference-heading"><ScanFace size={19}/><span>Ảnh nhân vật:</span>{scene.reference && <button className="remove-image" aria-label={`Gỡ ảnh cảnh ${scene.id}`} disabled={locked} onClick={() => changeScene(scene.id, { reference: null })}><X size={12}/></button>}</div>
            {scene.reference ? <button className="scene-image" disabled={locked} aria-label={`Đổi ảnh cảnh ${scene.id}`} onClick={() => void chooseImage(scene.id)}>{scene.reference.url ? <img src={scene.reference.url} alt={`Nhân vật cảnh ${scene.id}`}/> : <ScanFace size={24}/>}<span>{scene.reference.id === globalImage?.id ? 'Ảnh chung · đã đồng bộ' : 'Ảnh riêng'}<small>Nhấn để đổi ảnh</small></span></button> : <button className="select-image" disabled={locked} onClick={() => void chooseImage(scene.id)}><ImagePlus size={18}/>+ Chọn ảnh nhân vật</button>}
            {globalImage && scene.reference?.id !== globalImage.id && <button className="paste-image" disabled={locked} onClick={() => changeScene(scene.id, { reference: globalImage })}><Copy size={10}/>Dùng ảnh chung</button>}
          </div>
          <div className="prompt-label"><label htmlFor={`prompt-${scene.id}`}>Kịch bản Prompt:</label><button disabled={locked || renderBlocked || settings.mode === 'demo' || !scene.prompt.trim() || !scene.enabled} onClick={() => void enhance(scene)} title="Dịch và trau chuốt prompt bằng AI">{scene.enhancing ? <LoaderCircle size={18} className="spin"/> : <WandSparkles size={19}/>}AI Enhance</button></div>
          <textarea id={`prompt-${scene.id}`} aria-label={`Kịch bản cảnh ${scene.id}`} disabled={locked} maxLength={8000} value={scene.prompt} onChange={e => changeScene(scene.id, { prompt: e.target.value })} placeholder="Nhập mô tả phân cảnh…"/>
          {scene.error && <div className="scene-error"><span><CircleAlert size={13}/>{errorInfo(scene.error).hint}</span><details><summary>Mã lỗi gốc</summary><pre>{scene.error}</pre></details></div>}
        </div>
        <footer className="card-footer"><button className={`scene-run ${scene.video ? 'has-result' : ''}`} disabled={locked || renderBlocked || !scene.enabled || !scene.prompt.trim()} onClick={() => void run([scene.id])}>{scene.video || scene.status === 'error' ? <RefreshCw size={15}/> : <Play size={15}/>} {scene.video ? 'Tạo lại cảnh' : scene.status === 'error' ? 'Thử lại cảnh này' : 'Tạo cảnh này'}</button>{scene.video && <button className="download-one" title={`Tải cảnh ${scene.id}`} aria-label={`Tải cảnh ${scene.id}`} onClick={() => void downloadVideo(scene.video!, scene.id).catch(e => setNotice(logError(e, 'Tải video').raw))}><Download size={16}/></button>}</footer>
      </article>)}</section>
      <footer className="workspace-footer"><span><i/>Tự lưu kịch bản trên trình duyệt <span className="footer-divider">/</span> Ảnh & video chỉ giữ trong phiên</span><div><label className={`footer-button ${locked ? 'muted' : ''}`}><Upload size={13}/>Mở dự án<input type="file" accept=".json" hidden disabled={locked} onChange={e => { void restoreProject(e.target.files?.[0]); e.target.value = ''; }}/></label><button onClick={exportProject}><Download size={13}/>Xuất dự án JSON</button></div></footer>
    </main>
    {notice && <div className="toast" role="status"><CircleAlert size={17}/><span>{notice}</span><button aria-label="Đóng thông báo" onClick={() => setNotice('')}><X size={15}/></button></div>}

    {modal === 'import' && <Modal title="Nhập kịch bản thông minh" eyebrow="SCRIPT IMPORT / 10 SCENES" close={() => setModal(null)}>
      <div className="modal-body"><p className="muted">TXT: mỗi dòng hoặc mỗi đoạn là một cảnh. SRT: mỗi khối phụ đề là một cảnh, tự bỏ số thứ tự và timestamp. Tối đa 10 cảnh.</p><div className="preset-row"><button className="button" onClick={() => setImportText(ADVENTURE.join('\n\n'))}><Film size={16}/>Điện ảnh phiêu lưu</button><button className="button" onClick={() => setImportText(RUNWAY.join('\n\n'))}><WandSparkles size={16}/>Thời trang Runway</button><button className="button" onClick={() => fileInput.current?.click()}><Upload size={16}/>Chọn TXT / SRT</button></div>
        <textarea className="import-text" aria-label="Nội dung TXT / SRT" value={importText} onChange={e => setImportText(e.target.value)} placeholder={'Dán kịch bản hoặc phụ đề vào đây…\n\n1\n00:00:00,000 --> 00:00:04,000\nMột người thám hiểm bước vào ngôi đền cổ.'}/>
        <div className="import-count"><b className={parsed.length > 10 ? 'red' : 'mint'}>{parsed.length}/10 cảnh</b><span>{parsed.length > 10 ? 'Có hơn 10 cảnh. Rút gọn trước khi nạp, không tự cắt bỏ nội dung.' : parsed.length < 10 ? 'Các ô còn lại sẽ được để trống.' : 'Đã đủ 10 phân cảnh.'}</span></div>
        <div className="script-preview">{parsed.slice(0, 10).map((text, i) => <div key={i}><span>#{String(i + 1).padStart(2, '0')}</span><p>{text}</p></div>)}</div><p className="small muted">Nạp kịch bản sẽ thay prompt và xóa kết quả video cũ của 10 cảnh. Giữ ảnh tham chiếu và tài khoản.</p>
      </div><footer className="modal-footer"><button className="button" onClick={() => setModal(null)}>Đóng</button><button className="button" disabled={!canImport || locked} onClick={() => importScenes(false)}>Nạp vào Studio</button><button className="button primary" disabled={!canImport || locked || renderBlocked} onClick={() => importScenes(true)}><Play size={15}/>Nạp & Chạy các cảnh</button></footer>
    </Modal>}

    {modal === 'accounts' && <Modal title="Quản lý 10 tài khoản Muse" eyebrow="ACCOUNT POOL / PROMPT CONTROL" close={() => setModal(null)}>
      <div className="modal-body"><div className="info-note"><Users size={18}/><span>Email là nhãn phân công từng cảnh. Không đăng nhập, chuyển phiên hay tăng hạn mức. Mỗi slot gửi accountId riêng đến kết nối Muse AI. Tài khoản cần được xác thực qua API hoặc adapter của nhà cung cấp.</span></div>
        <div className="account-list">{scenes.map(scene => <div key={scene.id}><span className="scene-number">#{String(scene.id).padStart(2, '0')}</span><input aria-label={`Email tài khoản ${scene.id}`} type="email" disabled={locked} value={scene.email} maxLength={120} onChange={e => changeScene(scene.id, { email: e.target.value }, false)}/><label className="checkbox-label"><input type="checkbox" disabled={locked} checked={scene.enabled} onChange={e => changeScene(scene.id, { enabled: e.target.checked }, false)}/>{scene.enabled ? 'Kích hoạt' : 'Đã tắt'}</label></div>)}</div>
        <label className="field-label" htmlFor="email-bulk">Dán nhanh danh sách email</label><textarea id="email-bulk" className="bulk-text" value={emailText} disabled={locked} onChange={e => setEmailText(e.target.value)} placeholder="Mỗi dòng một email, hoặc dán cả danh sách…"/><button className="button" disabled={locked || !extractEmails(emailText).length} onClick={() => { const emails = extractEmails(emailText); updateScenes(all => all.map((s, i) => emails[i] ? { ...s, email: emails[i] } : s)); setNotice(`Đã cập nhật ${emails.length} nhãn tài khoản.`); }}><CheckCheck size={16}/>Điền {extractEmails(emailText).length} email hợp lệ</button>
        <label className="field-label" htmlFor="global-modifier">Chỉ thị chất lượng toàn cục <span className="tag">GLOBAL PROMPT MODIFIER</span></label><textarea id="global-modifier" className="bulk-text" disabled={locked} maxLength={2000} value={settings.modifier} onChange={e => changeSettings({ modifier: e.target.value })} placeholder="cinematic lighting, photorealistic, professional 35mm lens…"/><p className="small muted">Nối vào cuối mọi prompt gửi tạo video. Thay đổi chỉ thị sẽ xóa kết quả cũ để tránh dùng video không còn khớp kịch bản.</p>
      </div><footer className="modal-footer"><span className="small muted">{enabled}/10 tài khoản đang bật · Tự lưu</span><button className="button primary" onClick={() => setModal(null)}><Check size={16}/>Hoàn tất</button></footer>
    </Modal>}

    {modal === 'diagnostics' && <Modal title="Chẩn đoán & kết nối API" eyebrow="CONNECTION / HEALTH / ERROR LOG" close={() => setModal(null)}>
      <div className="modal-body"><label className="field-label" htmlFor="provider-mode">Kết nối tạo video</label><select id="provider-mode" className="provider-select" disabled={locked} value={settings.mode} onChange={e => { const mode = e.target.value as Mode; changeSettings({ mode }); setDiagnostic(null); setDiagnosticConsent(false); }}><option value="muse">Muse AI API · Web độc lập</option><option value="demo">Kiểm thử giao diện · Không tạo video AI</option></select>
        <div className="connection-details"><Link2 size={18}/><div><strong>{connection}</strong><p>{settings.mode === 'muse' ? 'Cần API hoặc adapter Muse AI đã xác thực các tài khoản. Chỉ nhập email không tạo kết nối. Xem README để cấu hình; hỗ trợ mô hình, R2V và hạn mức phụ thuộc dịch vụ Muse thực tế.' : 'Clip màu có nhãn TEST CLIP dùng để kiểm tra phát, tải và hàng đợi. Không đọc nội dung prompt, không thay cho video AI.'}</p></div></div>
        {renderBlocked && <div className="setup-help"><h3>Cần gì để tạo video thật?</h3><p>Bản web chưa có adapter tạo video Muse.ai thực tế. Các email là nhãn phân công, không phải phiên đăng nhập.</p><ol><li>Cần tài liệu API tạo video của Muse AI, kèm phương thức xác thực tài khoản chính thức.</li><li>Sau khi có adapter tương thích, cấu hình địa chỉ và thông tin xác thực trên máy chủ rồi khởi động lại tool.</li><li>Bấm Đọc cấu hình; chỉ chạy render thử khi có kết nối.</li></ol><a href="https://muse.ai/" target="_blank" rel="noopener noreferrer">Mở trang tài khoản Muse.ai</a><p className="small muted">Tính năng và mô hình khả dụng cần được xác nhận bằng API Muse thực tế. Chế độ kiểm thử chỉ phát clip mẫu có nhãn.</p>{statusError && <pre>{statusError}</pre>}</div>}
        <div className="diagnostic-stats"><div><span>TRẠNG THÁI</span><b>{diagnosticBusy ? 'Đang kiểm tra…' : busy ? 'Đang có tác vụ' : 'Chờ kiểm tra'}</b></div><div><span>CREDIT</span><b>Không được API cung cấp</b></div><div><span>GPU</span><b>Không được API cung cấp</b></div></div>
        <label className="checkbox-label consent"><input type="checkbox" checked={diagnosticConsent} disabled={locked} onChange={e => setDiagnosticConsent(e.target.checked)}/><span>{settings.mode === 'demo' ? 'Tôi muốn chạy clip kiểm thử giao diện.' : `Tôi đồng ý gửi một yêu cầu render thử (${settings.model === 'Omni 1.1 Flash' ? '4s / 360p' : '8s / 720p'}), có thể tính phí theo tài khoản AI.`}</span></label>
        <div className="preset-row"><button className="button primary" disabled={!diagnosticConsent || locked || renderBlocked} onClick={() => void diagnose()}>{diagnosticBusy ? <LoaderCircle size={17} className="spin"/> : <Activity size={17}/>}Kiểm tra render thực tế</button><button className="button" disabled={locked || statusLoading} onClick={() => void refreshStatus()}><RefreshCw size={15}/>Đọc cấu hình</button>{diagnosticBusy && <button className="button danger" onClick={cancel}><Square size={15}/>Dừng chờ</button>}</div>
        {diagnostic && <div className={`diagnostic-result ${diagnostic.error ? 'failed' : ''}`} role="status"><p>{diagnostic.message}</p>{diagnostic.error && <pre>{diagnostic.error}</pre>}</div>}
        <div className="log-heading"><h3>Nhật ký lỗi gần nhất <span>{logs.length}</span></h3><button disabled={!logs.length} onClick={() => setLogs([])}><Trash2 size={13}/>Xóa nhật ký</button></div><div className="error-log">{logs.length ? logs.map((log, i) => <details key={i}><summary><span>{log.time}</span>{log.scene}<ChevronDown size={13}/></summary><p>{log.hint}</p><pre>{log.raw}</pre></details>) : <p className="muted">Chưa có lỗi được ghi nhận trong phiên này.</p>}</div>
      </div><footer className="modal-footer"><span className="small muted">Thông tin đăng nhập không lưu trong trình duyệt hoặc dự án.</span><button className="button" onClick={() => setModal(null)}>Đóng</button></footer>
    </Modal>}
  </div>;
}

createRoot(document.getElementById('root')!).render(<App/>);
