'use strict';

const $ = (id) => document.getElementById(id);
const activeStatuses = new Set(['queued', 'running', 'cancelling']);
const statusNames = {queued: 'Trong hàng đợi', running: 'Đang tạo', cancelling: 'Đang dừng', cancelled: 'Đã dừng', error: 'Có lỗi', done: 'Hoàn tất'};
const deliveryNotes = {
  natural: 'Giữ nhịp đọc mặc định, nghỉ nhẹ giữa câu.',
  story: 'Nhịp chậm hơn, khoảng nghỉ dài hơn để kể chuyện. Cảm xúc phụ thuộc giọng và mô hình.',
  news: 'Nhịp đọc gọn, hơi nhanh, phù hợp bản tin hoặc lời review. Không tự viết hay biên tập kịch bản.',
  calm: 'Giảm nhịp và kéo dài khoảng nghỉ để đọc chậm rãi.',
  energetic: 'Tăng nhịp, rút ngắn khoảng nghỉ. Không điều khiển cảm xúc riêng của mô hình.'
};
let config = null;
let voices = [];
let history = [];
let selectedJob = null;
let currentView = 'create';
let submitting = false;
let polling = false;
let pollTimer;
let outputSignature = '';
let connectionFailed = false;
let renderSettingsInitialized = false;
let deliveryProfiles = new Map();
let paragraphPauseEdited = false;
const historyNodes = new Map();

function node(tag, text, className) {
  const el = document.createElement(tag);
  if (text !== undefined && text !== null) el.textContent = text;
  if (className) el.className = className;
  return el;
}

function notify(message, isError = false) {
  $('notice').textContent = message;
  $('notice').classList.toggle('error', isError);
  $('notice').hidden = !message;
}

async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(path, {cache: 'no-store', ...options});
  } catch {
    throw new Error('Mất kết nối với tool. Giữ cửa sổ chạy ứng dụng mở; nếu đã đóng, mở lại tool rồi làm mới trang.');
  }
  if (!response.ok) {
    let detail;
    try { detail = (await response.json()).detail; } catch { /* Non-JSON errors use a safe default. */ }
    throw new Error(typeof detail === 'string' ? detail : `Yêu cầu chưa thành công (${response.status}). Kiểm tra dữ liệu và thử lại.`);
  }
  return response.status === 204 ? null : response.json();
}

function post(path, data) {
  return api(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)});
}

function setConnection(online) {
  $('connection').className = `connection ${online ? 'ready' : 'offline'}`;
  $('connection').textContent = online
    ? `${config?.hardware || 'Máy cá nhân'} · Xử lý trên máy · ${config?.available_ram_gb ?? '?'} GB RAM còn trống`
    : 'Chưa kết nối được phòng thu';
}

function showView(view) {
  currentView = view;
  for (const section of document.querySelectorAll('.view')) section.hidden = section.id !== `view-${view}`;
  for (const button of document.querySelectorAll('[data-view]')) {
    const selected = button.dataset.view === view;
    button.classList.toggle('active', selected);
    if (selected) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  }
}

function voiceReady(voice) {
  if (!voice || !config) return false;
  if (voice.engine === 'system') return true;
  if (typeof voice.ready === 'boolean') return voice.ready;
  return voice.engine === 'vieneu_nano' ? Boolean(config.nano_ready) : Boolean(config.models?.[voice.engine]);
}

function modelInstruction(voice) {
  if (voice?.engine === 'vieneu_nano') return 'TAI_GIONG_VIET.bat';
  if (voice?.engine === 'vieneu') return 'TAI_GIONG_TIEU_CHUAN.bat';
  return 'TAI_GIONG_QUOC_TE.bat';
}

function languageName(language) { return config?.languages?.[language] || language || 'Chưa rõ ngôn ngữ'; }
function engineName(voice) {
  return {vieneu_nano: 'Nano', vieneu: 'VieNeu', qwen: 'Qwen', qwen_clone: 'Qwen · Nhân bản', system: 'Hệ thống Windows'}[voice?.engine] || voice?.engine || 'AI';
}

function populateDeliveryProfiles() {
  const previous = $('delivery').value;
  const catalog = config.delivery_profiles || config.profile_catalog || [];
  const entries = Array.isArray(catalog) ? catalog : Object.entries(catalog).map(([id, profile]) => ({id, ...profile}));
  deliveryProfiles = new Map(entries.filter((profile) => profile?.id).map((profile) => [profile.id, profile]));
  for (const profile of deliveryProfiles.values()) {
    let option = [...$('delivery').options].find((item) => item.value === profile.id);
    if (!option) { option = node('option'); option.value = profile.id; $('delivery').append(option); }
    option.textContent = profile.label || profile.id;
  }
  if ([...$('delivery').options].some((option) => option.value === previous)) $('delivery').value = previous;
  updateDelivery();
}

function normalizeSpeaker(value) { return String(value || '').normalize('NFC').trim().toLocaleLowerCase('vi'); }

function suggestedVoice() {
  const profile = deliveryProfiles.get($('delivery').value);
  const current = voices.find((voice) => voice.id === $('voice').value);
  const names = (profile?.recommended_speakers || profile?.suggested_speakers)?.[current?.engine];
  if (!Array.isArray(names)) return null;
  for (const name of names) {
    const match = voices.find((voice) => voice.engine === current.engine && voice.category !== 'cloned'
      && (voice.languages || []).includes($('language').value) && voiceReady(voice)
      && [voice.speaker, voice.name?.split(' · ')[0]].some((value) => normalizeSpeaker(value) === normalizeSpeaker(name)));
    if (match) return match;
  }
  return null;
}

function updateSuggestion() {
  const suggested = suggestedVoice();
  $('suggest-voice').disabled = !suggested || submitting;
  $('suggest-voice').title = suggested ? `Giọng gợi ý: ${suggested.name}` : 'Chưa có giọng gợi ý sẵn sàng cho loại giọng và ngôn ngữ đang chọn.';
}

function updateDelivery() {
  const profile = deliveryProfiles.get($('delivery').value);
  const detail = profile?.description || deliveryNotes[$('delivery').value] || 'Điều chỉnh nhịp và khoảng nghỉ theo thể loại.';
  $('delivery-note').textContent = `${detail} Sắc thái phụ thuộc giọng có sẵn hoặc mẫu thu cá nhân; nghe thử để chọn cảm xúc phù hợp.`;
  if (!paragraphPauseEdited && Number.isFinite(Number(profile?.pause))) $('paragraph-pause').value = String(profile.pause);
  updateSuggestion();
  updateRenderNote();
}

function fastNanoVoice() {
  if ($('language').value !== 'vi') return null;
  const profile = deliveryProfiles.get($('delivery').value);
  const recommendations = (profile?.recommended_speakers || profile?.suggested_speakers)?.vieneu_nano || [];
  for (const name of [...recommendations, 'Minh Quân']) {
    const match = voices.find((voice) => voice.engine === 'vieneu_nano' && voice.category !== 'cloned'
      && (voice.languages || []).includes('vi') && voiceReady(voice)
      && [voice.speaker, voice.name?.split(' · ')[0]].some((value) => normalizeSpeaker(value) === normalizeSpeaker(name)));
    if (match) return match;
  }
  return null;
}

function updateRenderNote() {
  const current = voices.find((voice) => voice.id === $('voice').value);
  let note = {
    balanced: 'Cân bằng tốc độ và độ tự nhiên. Đo mẫu để ước tính thời gian tạo trên máy này.',
    quality: 'Ưu tiên độ tự nhiên. Thời gian tạo có thể dài hơn; nghe mẫu để kiểm tra sắc thái và phát âm.',
    fast: 'Ưu tiên hoàn thành nhanh. Nghe mẫu để kiểm tra phát âm và độ tự nhiên trước khi tạo bản dài.'
  }[$('render-mode').value] || '';
  if ($('render-mode').value === 'fast' && current && current.engine !== 'vieneu_nano') {
    note = `Đang dùng ${current.name} · ${engineName(current)}. Tốc độ tạo phụ thuộc mô hình của giọng này. Chọn một giọng Nano để dùng cấu hình Nano ưu tiên tốc độ.`;
  }
  $('render-note').textContent = note;
  const nano = fastNanoVoice();
  $('choose-nano').disabled = !nano || submitting;
  $('choose-nano').title = nano ? `Chọn ${nano.name} và áp dụng ưu tiên tốc độ.` : 'Cần chọn tiếng Việt và tải giọng Nano trước khi sử dụng.';
}

function applyRenderMode(mode) {
  $('render-mode').value = mode;
  const preset = config?.rendering_presets?.[mode] || {};
  $('nano-steps').value = String(preset.nano_steps || {fast: 4, balanced: 8, quality: 16}[mode] || 8);
  $('nano-parallel').value = String(Math.max(1, Math.min(8, Number(preset.nano_parallel) || 1)));
  $('nano-threads').value = String(Math.max(1, Math.min(8, Number(preset.nano_threads) || 2)));
  $('audio-fit-backend').value = mode === 'fast' ? 'wsola' : (preset.audio_fit_backend === 'wsola' ? 'wsola' : 'ffmpeg');
  updateRenderNote();
}

async function inspectMachine() {
  const button = $('inspect-machine');
  button.disabled = true; button.textContent = 'Đang kiểm tra máy…';
  try {
    const info = await api('/api/system-info');
    if (info.rendering_presets && config) config.rendering_presets = info.rendering_presets;
    const gpuNames = Array.isArray(info.nvidia_gpus) ? info.nvidia_gpus : [];
    const rows = [
      ['Bộ xử lý', info.cpu || 'Chưa xác định'],
      ['Luồng CPU', info.logical_cores || 'Chưa xác định'],
      ['RAM', info.ram_gb == null ? 'Chưa xác định' : `${info.ram_gb} GB`],
      ['GPU NVIDIA', gpuNames.length ? gpuNames.join('; ') : 'Chưa tìm thấy'],
      ['Tăng tốc GPU cho giọng hỗ trợ', info.pytorch_cuda_available === true ? 'Sẵn sàng' : info.pytorch_cuda_available === false ? 'Chưa sẵn sàng' : 'Chưa xác định']
    ];
    const details = $('machine-details'); details.replaceChildren();
    for (const [label, value] of rows) details.append(node('dt', label), node('dd', String(value)));
    $('machine-note').textContent = info.note || 'Chọn Ưu tiên tốc độ, rồi đo mẫu để kiểm tra thời gian tạo trên máy này.';
    $('machine-report').hidden = false;
    notify('Đã kiểm tra máy đang chạy tool và cập nhật gợi ý cấu hình. Bấm Ưu tiên tốc độ để áp dụng, rồi đo mẫu.');
  } catch (error) { notify(error.message, true); }
  finally { button.disabled = false; button.textContent = 'Kiểm tra máy'; }
}

async function copyMachineReport() {
  const text = [...$('machine-details').children].map((item, index) => item.textContent + (index % 2 ? '\n' : ': ')).join('') + $('machine-note').textContent;
  try { await navigator.clipboard.writeText(text); notify('Đã sao chép thông tin máy. Bạn có thể dán báo cáo để được hỗ trợ.'); }
  catch { notify('Chưa sao chép được. Bạn có thể chọn và sao chép thông tin trong báo cáo máy.', true); }
}

function populateLanguages() {
  const previous = $('language').value;
  const available = new Set(config.ai_voice_languages || []);
  for (const voice of voices) if (voice.engine === 'system') for (const language of voice.languages || []) available.add(language);
  const options = Object.entries(config.languages || {}).filter(([key]) => available.has(key));
  $('language').replaceChildren(...options.map(([key, label]) => {
    const option = node('option', label); option.value = key; return option;
  }));
  if (available.has(previous)) $('language').value = previous;
  else if (available.has('vi')) $('language').value = 'vi';
  $('language').disabled = !options.length;
  const cloneLanguage = $('clone-language').value;
  $('clone-language').replaceChildren(...Object.entries(config.languages || {}).filter(([key]) => (config.ai_voice_languages || []).includes(key)).map(([key, label]) => {
    const option = node('option', label); option.value = key; return option;
  }));
  if (cloneLanguage && (config.ai_voice_languages || []).includes(cloneLanguage)) $('clone-language').value = cloneLanguage;
  else if ((config.ai_voice_languages || []).includes('vi')) $('clone-language').value = 'vi';
  $('clone-language').disabled = !$('clone-language').options.length;
  $('clone-submit').disabled = !$('clone-language').options.length;
}

function populateVoices() {
  const previous = $('voice').value;
  const choices = voices.filter((voice) => (voice.languages || []).includes($('language').value));
  $('voice').replaceChildren(...choices.map((voice) => {
    const option = node('option', `${voice.name} · ${engineName(voice)}${voiceReady(voice) ? '' : ' · Chưa tải'}`);
    option.value = voice.id; return option;
  }));
  if (choices.some((voice) => voice.id === previous)) $('voice').value = previous;
  else {
    const preferred = choices.find((voice) => voice.engine === 'vieneu_nano' && voiceReady(voice)) || choices.find(voiceReady);
    if (preferred) $('voice').value = preferred.id;
  }
  if (!choices.length) {
    const option = node('option', 'Chưa có giọng cho ngôn ngữ này'); option.value = ''; $('voice').append(option);
  }
  $('voice').disabled = !choices.length;
  updateVoice();
}

function updateVoice() {
  const voice = voices.find((item) => item.id === $('voice').value);
  const ready = voiceReady(voice);
  $('voice-status').className = `voice-status ${ready ? 'ready' : 'missing'}`;
  $('voice-status-title').textContent = !voice ? 'Chưa có giọng phù hợp' : ready ? `${engineName(voice)} · Sẵn sàng sử dụng` : `${engineName(voice)} · Cần tải mô hình`;
  $('voice-status-detail').textContent = !voice ? 'Chọn ngôn ngữ khác hoặc thêm mẫu giọng cá nhân được hỗ trợ.' : ready ? (voice.description || 'Giọng đã có trên máy.') : `Trong thư mục tool, chạy ${modelInstruction(voice)}, rồi bấm Kiểm tra lại ở Thư viện giọng.`;
  $('generate').disabled = !ready || submitting;
  $('benchmark').disabled = !ready || submitting || $('language').value !== 'vi';
  $('benchmark').title = $('language').value === 'vi' ? 'Đo bằng giọng và chế độ ưu tiên đang chọn.' : 'Mẫu đo hiện hỗ trợ tiếng Việt.';
  updateSuggestion();
  updateRenderNote();
  $('generate-note').textContent = !voice ? 'Cần chọn giọng hỗ trợ ngôn ngữ lời đọc.' : !ready ? 'Tải mô hình trước khi tạo giọng. Mở Hướng dẫn để xem chi tiết.' : 'Tạo trên máy · Có thể dừng và tiếp tục trong Bản thu';
}

function updateCharacterCount() {
  const count = $('script').value.length;
  $('char-count').textContent = `${count.toLocaleString('vi-VN')} / 1.000.000`;
  $('char-count').classList.toggle('limit', count >= 1000000);
}

function updateFormat() {
  const srt = $('script-format').value === 'srt';
  $('skip-timestamps').disabled = srt;
  $('cue-tempo').disabled = $('cue-fit').value === 'auto';
  $('format-note').textContent = srt ? ($('cue-fit').value === 'auto' ? 'SRT · Tự căn từng câu, giữ mốc gốc' : 'SRT · Giữ mốc thời gian') : 'TXT · Văn bản thuần';
}

function duration(seconds) {
  const value = Math.max(0, Math.floor(Number(seconds) || 0));
  return `${Math.floor(value / 3600)}:${String(Math.floor(value / 60) % 60).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`;
}

function jobPath(job, suffix = '') { return `/api/jobs/${encodeURIComponent(job.id)}${suffix}`; }
function makeButton(text, onClick, className = 'secondary-button') {
  const button = node('button', text, className); button.type = 'button';
  button.addEventListener('click', async () => {
    button.disabled = true;
    try { await onClick(); } catch (error) { notify(error.message, true); }
    finally { button.disabled = false; }
  });
  return button;
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const anchor = node('a'); anchor.href = url; anchor.download = filename;
  document.body.append(anchor); anchor.click(); anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}

async function downloadExport(job, extension) {
  notify('');
  let response;
  try { response = await fetch(jobPath(job, `/export.${extension}`)); }
  catch { throw new Error('Mất kết nối khi tải tệp. Mở lại tool và thử lại.'); }
  if (!response.ok) {
    let detail;
    try { detail = (await response.json()).detail; } catch { /* Use a generic download error. */ }
    throw new Error(typeof detail === 'string' ? detail : 'Chưa tải được tệp. Kiểm tra tool và thử lại.');
  }
  downloadBlob(await response.blob(), `voice-${job.id.slice(0, 8)}.${extension}`);
}

function addExportButtons(container, job) {
  for (const extension of ['wav', 'mp3', 'txt', 'srt']) {
    container.append(makeButton(`↓ ${extension.toUpperCase()}`, () => downloadExport(job, extension)));
  }
}

async function cancelJob(job) {
  const updated = await api(jobPath(job, '/cancel'), {method: 'POST'});
  if (selectedJob?.id === job.id) setOutput(updated);
  await refreshHistory();
  notify('Đã yêu cầu dừng. Những đoạn đã tạo được giữ lại để tiếp tục.');
}

async function resumeJob(job) {
  const updated = await api(jobPath(job, '/resume'), {method: 'POST'});
  setOutput(updated);
  await refreshHistory();
  showView('create');
  $('output-heading').scrollIntoView({block: 'center', behavior: 'auto'});
  notify(job.input_format === 'srt' ? 'Đã bật tự căn theo mốc và tiếp tục; dùng lại các đoạn đã tạo.' : 'Đã đưa bản thu vào hàng đợi để tiếp tục.');
}

function addJobControls(container, job) {
  if (job.status === 'done') addExportButtons(container, job);
  if (activeStatuses.has(job.status)) {
    const stop = makeButton(job.status === 'cancelling' ? 'Đang dừng…' : '■ Dừng tạo', () => cancelJob(job));
    stop.disabled = job.status === 'cancelling'; container.append(stop);
  }
  if (['error', 'cancelled'].includes(job.status)) container.append(makeButton(job.input_format === 'srt' ? '▷ Tự căn và tiếp tục' : '▷ Tiếp tục bản thu', () => resumeJob(job)));
}

function setOutput(job) {
  selectedJob = job;
  const signature = JSON.stringify([job.id, job.status, job.progress, job.phase, job.error, job.audio_seconds, job.duration_limited, job.speed_report, job.auto_fitted_cues, job.fit_warning_count, job.benchmark_note]);
  if (outputSignature === signature) return;
  outputSignature = signature;
  const progress = Math.max(0, Math.min(100, Number(job.progress) || 0));
  $('output-heading').textContent = {
    queued: 'Bản thu đã vào hàng đợi', running: 'Đang tạo giọng nói…', cancelling: 'Đang dừng bản thu…',
    cancelled: 'Đã dừng · Có thể tiếp tục', error: 'Bản thu cần được kiểm tra', done: 'Bản thu đã sẵn sàng'
  }[job.status] || 'Bản thu của bạn';
  $('output-status').hidden = false;
  $('output-status').className = `status-badge ${job.status}`;
  $('output-status').textContent = `${statusNames[job.status] || job.status}${activeStatuses.has(job.status) ? ` · ${progress}%` : ''}`;
  $('output-detail').textContent = `${job.voice_name || 'Giọng đọc'} · ${languageName(job.language)} · ${duration(job.audio_seconds)}${job.phase ? ` · ${job.phase}` : ''}`;
  $('output-progress').hidden = !activeStatuses.has(job.status);
  $('output-progress').value = progress;
  const fitWarning = job.fit_warning_count ? `Đã tự căn ${job.auto_fitted_cues || 0} câu. ${job.fit_warning_count} câu cần tăng tốc trên 2×${job.fit_warning_cues?.length ? ' (câu ' + job.fit_warning_cues.slice(0, 10).join(', ') + (job.fit_warning_cues.length > 10 ? ', …' : '') + ')' : ''}; nghe kiểm tra trước khi dựng video.` : '';
  const warning = job.error || fitWarning || (job.duration_limited ? 'Đã đạt giới hạn thời lượng. Phần nội dung còn lại chưa được đọc; chia lời đọc thủ công hoặc tăng giới hạn (tối đa 1440 phút) để tạo lại.' : '');
  $('output-warning').textContent = warning; $('output-warning').hidden = !warning;
  $('benchmark-note').textContent = job.benchmark_note || '';
  $('benchmark-note').hidden = !job.benchmark_note;
  const done = job.status === 'done';
  $('output-audio').hidden = !done;
  if (done) {
    const url = `/api/audio/${encodeURIComponent(job.id)}`;
    if ($('output-audio').getAttribute('src') !== url) $('output-audio').src = url;
  } else if ($('output-audio').hasAttribute('src')) {
    $('output-audio').pause(); $('output-audio').removeAttribute('src'); $('output-audio').load();
  }
  $('output-actions').replaceChildren(); addJobControls($('output-actions'), job);
  const report = job.speed_report;
  $('speed-report').hidden = !done || !report;
  $('speed-report').textContent = report ? formatSpeedReport(report) : '';
}

function formatSpeedReport(report) {
  const multiplier = Number(report.spoken_realtime_multiplier ?? report.realtime_multiplier);
  const seconds = Number(report.estimated_hour_seconds);
  const measuredSeconds = Number(report.voiced_seconds ?? report.measurement_audio_seconds);
  const elapsed = Number(report.measurement_elapsed_seconds);
  const number = (value) => value.toLocaleString('vi-VN', {maximumFractionDigits: 2});
  const parts = [];
  if (Number.isFinite(multiplier) && multiplier > 0) parts.push(`Tốc độ đo: ${number(multiplier)}× thời gian thực`);
  if (Number.isFinite(measuredSeconds) && Number.isFinite(elapsed)) parts.push(`${number(measuredSeconds)} giây ${report.voiced_seconds != null || report.excluded_silence_seconds != null ? 'lời đọc' : 'âm thanh'} / ${number(elapsed)} giây xử lý`);
  if (Number.isFinite(seconds) && seconds > 0) parts.push(`Ước tính tạo 1 giờ lời đọc: ${duration(Math.ceil(seconds))}`);
  if (typeof report.target_30x_met_on_sample === 'boolean') parts.push(report.target_30x_met_on_sample ? 'Mẫu đo đạt mục tiêu 30× (1 giờ trong 2 phút).' : 'Mẫu đo chưa đạt mục tiêu 30× (1 giờ trong 2 phút).');
  if (report.includes_silence) parts.push(report.voiced_seconds != null
    ? 'Ước tính dựa trên phần lời đọc; khoảng lặng trên timeline được tách riêng.'
    : 'Bản thu có khoảng lặng; tỷ lệ theo tổng thời lượng có thể cao hơn tốc độ tạo lời đọc thực.');
  else if (Number(report.excluded_silence_seconds) > 0) parts.push(`Đã loại ${number(Number(report.excluded_silence_seconds))} giây khoảng lặng khỏi phép đo tốc độ lời đọc.`);
  parts.push(report.estimate_only
    ? 'Đây là ước tính từ mẫu ngắn, chưa phải kết quả tạo đủ 1 giờ; bản dài có thể khác.'
    : 'Thời gian tạo bản khác thay đổi theo giọng, nội dung và tài nguyên máy.');
  return parts.join(' · ');
}

async function generate() {
  if (submitting) return;
  if (!$('script').value.trim()) { notify('Hãy nhập nội dung cần đọc.', true); $('script').focus(); return; }
  if ($('script').value.length > 1000000) { notify('Mỗi lần tạo nhận tối đa 1.000.000 ký tự.', true); return; }
  for (const id of ['max-minutes', 'paragraph-pause', 'nano-threads']) if (!$(id).reportValidity()) return;
  const voice = voices.find((item) => item.id === $('voice').value);
  if (!voiceReady(voice)) { notify('Chọn một giọng đã sẵn sàng hoặc tải mô hình trước.', true); return; }
  submitting = true; updateVoice(); notify('');
  try {
    const job = await post('/api/speech', {
      text: $('script').value, voice_id: voice.id, language: $('language').value,
      input_format: $('script-format').value, skip_timestamps: $('skip-timestamps').checked,
      speed: Number($('speed').value), format: $('format').value,
      max_minutes: Number($('max-minutes').value), delivery: $('delivery').value,
      paragraph_pause: paragraphPauseEdited ? Number($('paragraph-pause').value) : null, quality: $('quality').value,
      cue_fit: $('cue-fit').value, max_cue_tempo: Number($('cue-tempo').value),
      render_mode: $('render-mode').value, audio_fit_backend: $('audio-fit-backend').value,
      nano_steps: Number($('nano-steps').value), nano_threads: Number($('nano-threads').value), nano_parallel: Number($('nano-parallel').value)
    });
    setOutput(job); notify('Đã nhận nội dung. Bạn có thể theo dõi bản thu ở bên dưới.');
    await refreshHistory();
  } catch (error) { notify(error.message, true); }
  finally { submitting = false; updateVoice(); }
}

async function benchmark() {
  if (submitting) return;
  if ($('language').value !== 'vi') { notify('Mẫu đo tốc độ hiện hỗ trợ tiếng Việt. Chọn tiếng Việt để đo thử.', true); return; }
  const voice = voices.find((item) => item.id === $('voice').value);
  if (!voiceReady(voice)) { notify('Chọn giọng đã sẵn sàng trước khi đo tốc độ.', true); return; }
  submitting = true; updateVoice(); notify('');
  try {
    const job = await post('/api/benchmark', {
      voice_id: voice.id, language: $('language').value,
      render_mode: $('render-mode').value, delivery: $('delivery').value,
      nano_steps: Number($('nano-steps').value), nano_parallel: Number($('nano-parallel').value),
      nano_threads: Number($('nano-threads').value), audio_fit_backend: $('audio-fit-backend').value, quality: $('quality').value
    });
    setOutput(job);
    notify('Đang tạo mẫu ngắn để đo tốc độ. Kết quả và ước tính tạo 1 giờ lời đọc sẽ hiện ở Bản thu.');
    await refreshHistory();
    $('output-heading').scrollIntoView({block: 'center', behavior: 'auto'});
  } catch (error) { notify(error.message, true); }
  finally { submitting = false; updateVoice(); }
}

async function importScript(file) {
  if (!file) return;
  if (!/\.(txt|srt)$/i.test(file.name)) throw new Error('Chọn tệp có đuôi .txt hoặc .srt.');
  if (file.size > 8 * 1024 * 1024) throw new Error('Tệp văn bản không được vượt quá 8 MB.');
  const data = new FormData(); data.append('file', file);
  const imported = await api('/api/scripts/import', {method: 'POST', body: data});
  const text = imported.text, format = imported.input_format;
  if ($('script').value.trim() && !window.confirm('Thay nội dung đang nhập bằng nội dung trong tệp?')) return;
  $('script').value = text; $('script-format').value = format;
  if (imported.duration) $('max-minutes').value = Math.max(Number($('max-minutes').value), Math.ceil(imported.duration / 60));
  updateCharacterCount(); updateFormat();
  notify(`Đã nhập ${text.length.toLocaleString('vi-VN')} ký tự từ ${file.name}${format === 'srt' ? ' và giữ mốc thời gian' : ''}.`);
}

async function exportScript(extension) {
  const text = $('script').value;
  const format = $('script-format').value;
  if (!text.trim()) throw new Error('Chưa có nội dung để xuất.');
  if (extension === 'srt' && format === 'txt') {
    const job = history.find((item) => item.status === 'done' && item.input_format !== 'srt' && item.text.trim() === text.trim());
    if (!job) throw new Error('Tạo giọng hoàn tất với nội dung này trước khi xuất SRT để có mốc thời gian lời đọc thực.');
    await downloadExport(job, extension); return;
  }
  const result = await post('/api/scripts/convert', {text, input_format: format, output_format: extension});
  downloadBlob(new Blob([result.text], {type: 'text/plain;charset=utf-8'}), `loi-doc.${extension}`);
}

function renderLibrary() {
  const query = $('voice-search').value.trim().toLocaleLowerCase('vi');
  const filter = $('library-filter').value;
  const entries = voices.filter((voice) => (voice.name || '').toLocaleLowerCase('vi').includes(query))
    .filter((voice) => filter === 'all' || (filter === 'ready' && voiceReady(voice)) || (filter === 'cloned' && voice.category === 'cloned') || (filter === 'system' && voice.engine === 'system'));
  const library = $('voice-library'); library.replaceChildren();
  if (!entries.length) { library.append(node('div', 'Chưa có giọng phù hợp. Thử đổi bộ lọc hoặc thêm mẫu giọng bên dưới.', 'empty-state')); return; }
  for (const voice of entries) {
    const card = node('article', null, 'card voice-card');
    const heading = node('div', null, 'voice-card-heading');
    const icon = node('span', '≋', 'voice-icon'); icon.setAttribute('aria-hidden', 'true');
    const title = node('div'); title.append(node('h3', voice.name), node('p', engineName(voice)));
    heading.append(icon, title); card.append(heading, node('p', voice.description || 'Giọng đọc được cài trên máy.'));
    const tags = node('div', null, 'tags');
    tags.append(node('span', voice.category === 'cloned' ? 'GIỌNG CÁ NHÂN' : voice.engine === 'system' ? 'GIỌNG HỆ THỐNG' : 'GIỌNG CÓ SẴN', 'small-tag'));
    for (const language of (voice.languages || []).slice(0, 2)) tags.append(node('span', languageName(language), 'small-tag'));
    if ((voice.languages || []).length > 2) tags.append(node('span', `+${voice.languages.length - 2} ngôn ngữ`, 'small-tag'));
    card.append(tags);
    const ready = voiceReady(voice);
    card.append(node('p', ready ? '● Sẵn sàng sử dụng' : `○ Chưa tải · ${modelInstruction(voice)}`, `readiness ${ready ? 'ready' : 'missing'}`));
    if (voice.category === 'cloned') {
      const audio = node('audio'); audio.controls = true; audio.preload = 'none'; audio.src = `/api/voices/${encodeURIComponent(voice.id)}/sample`;
      audio.setAttribute('aria-label', `Nghe mẫu giọng ${voice.name}`); card.append(audio);
    }
    const controls = node('div', null, 'button-row');
    controls.append(makeButton('Chọn giọng →', async () => {
      const language = (voice.languages || []).find((value) => [...$('language').options].some((option) => option.value === value));
      if (!language) throw new Error('Chưa có ngôn ngữ phù hợp cho giọng này.');
      $('language').value = language; populateVoices(); $('voice').value = voice.id; updateVoice();
      showView('create'); $('script').focus();
      if (!ready) notify(`Giọng này cần mô hình. Chạy ${modelInstruction(voice)} trong thư mục tool rồi kiểm tra lại.`, true);
    }));
    if (voice.category === 'cloned') controls.append(makeButton('Xóa mẫu', async () => {
      if (!window.confirm(`Xóa mẫu và hồ sơ giọng “${voice.name}” khỏi máy?`)) return;
      await api(`/api/voices/${encodeURIComponent(voice.id)}`, {method: 'DELETE'}); await refreshVoices(); notify('Đã xóa mẫu giọng.');
    }, 'text-button danger-button'));
    card.append(controls); library.append(card);
  }
}

function historyCard(job) {
  const card = node('article', null, 'card history-item');
  const heading = node('div', null, 'history-heading');
  const title = node('div'); title.append(node('h2', job.voice_name || 'Bản thu'), node('p', `${languageName(job.language)} · ${new Date(job.created_at).toLocaleString('vi-VN')} · ${(job.format || 'wav').toUpperCase()}`, 'history-meta'));
  heading.append(title, node('span', statusNames[job.status] || job.status, `status-badge ${job.status}`));
  card.append(heading, node('p', (job.text || '').length > 220 ? `${job.text.slice(0, 220)}…` : job.text, 'history-excerpt'));
  card.append(node('p', `${Number(job.progress) || 0}% · ${duration(job.audio_seconds)}${job.completed !== undefined && job.total ? ` · ${job.completed}/${job.total} đoạn xử lý` : ''}${job.phase ? ` · ${job.phase}` : ''}`, 'field-note'));
  if (activeStatuses.has(job.status)) {
    const progress = node('progress'); progress.max = 100; progress.value = Number(job.progress) || 0; progress.setAttribute('aria-label', 'Tiến độ bản thu'); card.append(progress);
  }
  if (job.error) card.append(node('p', job.error, 'history-error'));
  if (job.duration_limited) card.append(node('p', 'Đã đạt giới hạn thời lượng; còn nội dung chưa đọc.', 'history-error'));
  if (job.status === 'done') {
    const audio = node('audio'); audio.controls = true; audio.preload = 'none'; audio.src = `/api/audio/${encodeURIComponent(job.id)}`;
    audio.setAttribute('aria-label', `Nghe bản thu ${job.voice_name || ''}`); card.append(audio);
  }
  const controls = node('div', null, 'history-controls'); const actions = node('div', null, 'button-row');
  addJobControls(actions, job);
  actions.append(makeButton('Mở bản thu ↗', async () => { setOutput(job); showView('create'); $('output-heading').scrollIntoView({block: 'center', behavior: 'auto'}); }));
  controls.append(actions);
  if (!activeStatuses.has(job.status)) controls.append(makeButton('Xóa', async () => {
    if (!window.confirm('Xóa bản thu và những tệp âm thanh của bản thu này khỏi máy?')) return;
    await api(`/api/history/${encodeURIComponent(job.id)}`, {method: 'DELETE'});
    if (selectedJob?.id === job.id) resetOutput();
    await refreshHistory(); notify('Đã xóa bản thu.');
  }, 'text-button danger-button'));
  card.append(controls); return card;
}

function resetOutput() {
  selectedJob = null; outputSignature = '';
  $('output-heading').textContent = 'Âm thanh của bạn sẽ xuất hiện ở đây';
  $('output-detail').textContent = 'Tạo bản thu đầu tiên hoặc mở một bản thu trong lịch sử.';
  for (const id of ['output-status', 'output-progress', 'output-warning', 'output-audio', 'speed-report', 'benchmark-note']) $(id).hidden = true;
  $('output-audio').pause(); $('output-audio').removeAttribute('src'); $('output-audio').load();
  $('output-actions').replaceChildren();
}

function renderHistory() {
  $('history-count').textContent = String(history.length);
  const list = $('history-list');
  if (!history.length) {
    historyNodes.clear(); list.replaceChildren(); const empty = node('div', null, 'empty-state');
    empty.append(node('strong', 'Chưa có bản thu nào'), node('span', 'Tạo giọng từ lời đọc của bạn; âm thanh và các tác vụ sẽ được lưu tại đây.'));
    list.append(empty); return;
  }
  if (list.firstElementChild?.classList.contains('empty-state')) list.replaceChildren();
  const ids = new Set(history.map((job) => job.id));
  for (const [id, entry] of historyNodes) if (!ids.has(id)) { entry.element.remove(); historyNodes.delete(id); }
  history.forEach((job, index) => {
    const signature = JSON.stringify([job.status, job.progress, job.phase, job.completed, job.audio_seconds, job.error, job.duration_limited]);
    let entry = historyNodes.get(job.id);
    if (!entry || entry.signature !== signature) {
      const element = historyCard(job);
      if (entry) entry.element.replaceWith(element);
      entry = {element, signature}; historyNodes.set(job.id, entry);
    }
    if (list.children[index] !== entry.element) list.insertBefore(entry.element, list.children[index] || null);
  });
}

async function refreshHistory() {
  const result = await api('/api/history');
  history = (result.items || []).filter((job) => /^[a-f0-9]{32}$/.test(job.id));
  renderHistory();
  if (selectedJob) {
    const updated = history.find((job) => job.id === selectedJob.id);
    if (updated) setOutput(updated);
  }
}

function renderModelStatus() {
  const target = $('model-status'); target.replaceChildren();
  target.append(node('p', `${config.hardware} · ${config.cpu_cores} luồng CPU · ${config.available_ram_gb ?? '?'} GB RAM trống`));
  target.append(node('p', `FFmpeg: ${config.ffmpeg ? 'Đã cài' : 'Chưa tìm thấy · chạy lại CAI_DAT.bat'}`));
  for (const [key, ready] of [['vieneu_nano', config.nano_ready], ...Object.entries(config.models || {})]) target.append(node('p', `${ready ? '●' : '○'} ${key}: ${ready ? 'Đã tải' : 'Chưa tải'}`));
  target.append(node('p', 'Giọng hệ thống Windows có thể dùng ngay khi đã được cài trong hệ điều hành.'));
}

async function refreshVoices() {
  const results = await Promise.all([api('/api/config'), api('/api/voices')]);
  config = results[0]; voices = results[1].voices || [];
  populateDeliveryProfiles();
  if (!renderSettingsInitialized) { applyRenderMode($('render-mode').value); renderSettingsInitialized = true; }
  populateLanguages(); populateVoices(); renderLibrary(); renderModelStatus();
  $('version').textContent = config.version ? `· ${config.version}` : '';
  setConnection(true);
}

async function cloneVoice(event) {
  event.preventDefault();
  if (!$('clone-form').reportValidity()) return;
  const file = $('clone-file').files[0];
  if (!file || !file.size || file.size > 20 * 1024 * 1024) { notify('Chọn mẫu giọng có dữ liệu, tối đa 20 MB.', true); return; }
  $('clone-submit').disabled = true; $('clone-submit').textContent = 'Đang lưu mẫu…'; notify('');
  try {
    const result = await api('/api/voices/clone', {method: 'POST', body: new FormData($('clone-form'))});
    await refreshVoices(); $('clone-form').reset();
    notify(`Đã lưu mẫu giọng “${result.name}”. Mẫu thu và mô hình quyết định độ giống; chọn giọng trong thư viện để tạo lời đọc.`);
    $('voices-heading').scrollIntoView({block: 'start', behavior: 'auto'});
  } catch (error) { notify(error.message, true); }
  finally { $('clone-submit').disabled = false; $('clone-submit').textContent = 'Lưu mẫu giọng →'; }
}

async function poll() {
  if (polling) return;
  polling = true;
  try {
    if (!config) await refreshVoices();
    await refreshHistory();
    if (connectionFailed) { setConnection(true); notify('Đã kết nối lại với phòng thu.'); connectionFailed = false; }
  } catch (error) {
    setConnection(false);
    if (!connectionFailed) notify(error.message, true);
    connectionFailed = true;
  } finally {
    polling = false;
    pollTimer = setTimeout(poll, document.hidden ? 12000 : 3000);
  }
}

for (const button of document.querySelectorAll('[data-view]')) button.addEventListener('click', () => showView(button.dataset.view));
$('language').addEventListener('change', populateVoices);
$('voice').addEventListener('change', updateVoice);
$('script').addEventListener('input', updateCharacterCount);
$('script-format').addEventListener('change', updateFormat);
$('speed').addEventListener('input', () => { $('speed-value').textContent = `${Number($('speed').value).toLocaleString('vi-VN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}×`; });
$('delivery').addEventListener('change', updateDelivery);
$('paragraph-pause').addEventListener('input', () => { paragraphPauseEdited = true; });
$('render-mode').addEventListener('change', () => applyRenderMode($('render-mode').value));
$('optimize-speed').addEventListener('click', () => {
  applyRenderMode('fast');
  notify('Đã áp dụng ưu tiên tốc độ theo tài nguyên máy. Bấm Đo tốc độ bằng mẫu ngắn để ước tính trước khi tạo bản dài.');
});
$('choose-nano').addEventListener('click', () => {
  const voice = fastNanoVoice();
  if (!voice) { notify('Chọn tiếng Việt và tải giọng Nano trước khi sử dụng.', true); return; }
  $('voice').value = voice.id; applyRenderMode('fast'); updateVoice();
  notify(`Đã chọn ${voice.name} và áp dụng ưu tiên tốc độ. Đo mẫu, rồi nghe kiểm tra trước khi tạo bản dài.`);
});
$('suggest-voice').addEventListener('click', () => {
  const suggested = suggestedVoice();
  if (!suggested) { notify('Chưa có giọng gợi ý sẵn sàng. Chọn giọng khác hoặc tải thêm giọng trong Thư viện giọng.', true); return; }
  $('voice').value = suggested.id; updateVoice();
  notify(`Đã chọn ${suggested.name} cho ${$('delivery').selectedOptions[0]?.textContent || 'thể loại đang chọn'}. Hãy nghe mẫu để đánh giá sắc thái.`);
});
$('benchmark').addEventListener('click', benchmark);
$('inspect-machine').addEventListener('click', inspectMachine);
$('copy-machine-report').addEventListener('click', copyMachineReport);
$('generate').addEventListener('click', generate);
$('import-script').addEventListener('click', () => $('script-file').click());
$('script-file').addEventListener('change', async () => {
  try { await importScript($('script-file').files[0]); } catch (error) { notify(error.message, true); }
  finally { $('script-file').value = ''; }
});
for (const extension of ['txt', 'srt']) $(`export-${extension}`).addEventListener('click', async () => {
  try { await exportScript(extension); } catch (error) { notify(error.message, true); }
});
$('voice-search').addEventListener('input', renderLibrary);
$('library-filter').addEventListener('change', renderLibrary);
$('refresh-voices').addEventListener('click', async () => {
  $('refresh-voices').disabled = true;
  try { await refreshVoices(); notify('Đã cập nhật giọng và tình trạng mô hình.'); } catch (error) { notify(error.message, true); }
  finally { $('refresh-voices').disabled = false; }
});
$('refresh-history').addEventListener('click', async () => {
  $('refresh-history').disabled = true;
  try { if (!config) await refreshVoices(); await refreshHistory(); notify('Đã cập nhật danh sách bản thu.'); } catch (error) { notify(error.message, true); }
  finally { $('refresh-history').disabled = false; }
});
$('clone-form').addEventListener('submit', cloneVoice);
$('help-open').addEventListener('click', () => $('help-dialog').showModal());
$('help-close').addEventListener('click', () => $('help-dialog').close());
document.addEventListener('visibilitychange', () => {
  if (!document.hidden && !polling) { clearTimeout(pollTimer); poll(); }
});
window.addEventListener('pagehide', () => clearTimeout(pollTimer));

async function init() {
  try {
    await refreshVoices(); await refreshHistory();
    if (history[0]) setOutput(history[0]);
    if (!voices.some(voiceReady)) notify('Phòng thu đã mở. Chưa có giọng sẵn sàng; xem Hướng dẫn để tải mô hình trước khi tạo âm thanh.');
  } catch (error) { notify(error.message, true); setConnection(false); connectionFailed = true; }
  pollTimer = setTimeout(poll, 3000);
}
init();

$('cue-fit').addEventListener('change', updateFormat);
