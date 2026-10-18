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
let benchmarking = false;
let polling = false;
let pollTimer;
let outputSignature = '';
let connectionFailed = false;
let defaultsApplied = false;
let importing = false;
let scriptPreview = null;
let scriptPreviewKey = '';
let scriptPreviewPromise = null;
let scriptPreviewRequest = 0;
let previewTimer;
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

function cloneReadyEngines(voice) {
  if (voice?.category !== 'cloned' || !config) return {};
  const languages = voice.languages || [];
  const engines = {};
  if (languages.includes('vi')) {
    engines.vieneu = Boolean(voice.ready_engines?.vieneu ?? config.models?.vieneu);
    engines.vieneu_nano = Boolean(voice.ready_engines?.vieneu_nano ?? config.nano_clone_ready);
  }
  if (languages.some((language) => language !== 'vi' && (config.ai_voice_languages || []).includes(language))) {
    engines.qwen_clone = Boolean(voice.ready_engines?.qwen_clone ?? config.models?.qwen_clone);
  }
  return engines;
}

function libraryVoiceReady(voice) {
  return voice?.category === 'cloned' ? Object.values(cloneReadyEngines(voice)).some(Boolean) : voiceReady(voice);
}

function cloneReadinessLabel(voice) {
  const engines = cloneReadyEngines(voice);
  const labels = [];
  if ('vieneu_nano' in engines) labels.push(`Nano ${engines.vieneu_nano ? 'sẵn sàng' : 'chưa tải'}`);
  if ('vieneu' in engines) labels.push(`Tiêu chuẩn ${engines.vieneu ? 'sẵn sàng' : 'chưa tải'}`);
  if ('qwen_clone' in engines) labels.push(`Quốc tế ${engines.qwen_clone ? 'sẵn sàng' : 'chưa tải'}`);
  return labels.join(' · ') || 'Chưa có mô hình hỗ trợ ngôn ngữ mẫu';
}

function modelInstruction(voice, engine = voice?.engine) {
  if (voice?.category === 'cloned') {
    if (engine === 'vieneu_nano') return 'TAI_GIONG_NHAN_BAN_NHANH.bat';
    return engine === 'vieneu' || (!engine && (voice.languages || []).includes('vi'))
      ? 'TAI_GIONG_TIEU_CHUAN.bat' : 'TAI_GIONG_QUOC_TE.bat';
  }
  if (engine === 'vieneu_nano') return 'TAI_GIONG_VIET.bat';
  if (engine === 'vieneu') return 'TAI_GIONG_TIEU_CHUAN.bat';
  return 'TAI_GIONG_QUOC_TE.bat';
}

function languageName(language) { return config?.languages?.[language] || language || 'Chưa rõ ngôn ngữ'; }
function searchText(value) {
  return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D').toLocaleLowerCase('vi');
}
function genderName(voice) {
  return {male: 'Nam', female: 'Nữ'}[voice?.gender] || '';
}
function voiceSearchText(voice) {
  return searchText([voice.name, voice.country, voice.description, engineName(voice), genderName(voice), ...(voice.languages || []).flatMap((language) => [language, languageName(language)])].join(' '));
}
function engineName(voice) {
  return {vieneu_nano: 'Nano', vieneu: 'VieNeu', piper: 'Piper · CPU nhanh', qwen: 'Qwen', qwen_clone: 'Qwen · Nhân bản', system: 'Hệ thống Windows'}[voice?.engine] || voice?.engine || 'AI';
}

function cloneEngine() {
  return $('language').value === 'vi' && voices.find((voice) => voice.id === $('voice').value)?.category === 'cloned'
    ? $('clone-engine').value : 'auto';
}

function selectedEngine(voice) {
  if (voice?.category !== 'cloned' || $('language').value !== 'vi') return voice?.engine;
  if (cloneEngine() === 'nano') return 'vieneu_nano';
  if (cloneEngine() === 'standard') return 'vieneu';
  return ['vieneu_nano', 'vieneu'].includes(voice.default_engine) ? voice.default_engine
    : cloneReadyEngines(voice).vieneu_nano ? 'vieneu_nano' : 'vieneu';
}

function selectedVoiceReady(voice) {
  if (voice?.category === 'cloned' && $('language').value === 'vi') {
    const engine = selectedEngine(voice);
    return Boolean(voice.ready_engines?.[engine] ?? (engine === 'vieneu_nano' ? config?.nano_clone_ready : config?.models?.vieneu));
  }
  return voiceReady(voice);
}

function populateLanguages() {
  const previous = $('language').value;
  const available = new Set(config.ai_voice_languages || []);
  for (const voice of voices) if (libraryVoiceReady(voice)) for (const language of voice.languages || []) available.add(language);
  const query = searchText($('language-search').value.trim());
  const options = [...available].map((key) => [key, languageName(key)]).filter(([key, label]) => !query || searchText(`${key} ${label}`).includes(query));
  $('language').replaceChildren(...options.map(([key, label]) => {
    const option = node('option', label); option.value = key; return option;
  }));
  if (options.some(([key]) => key === previous)) $('language').value = previous;
  else if (options.some(([key]) => key === 'vi')) $('language').value = 'vi';
  if (!options.length) {
    const option = node('option', 'Không tìm thấy quốc gia / ngôn ngữ'); option.value = ''; $('language').append(option);
  }
  $('language').disabled = !options.length;
  $('language-count').textContent = `${available.size} lựa chọn ngôn ngữ / quốc gia · ${voices.filter((voice) => voice.engine === 'piper' && voiceReady(voice)).length} giọng Piper có sẵn`;
  const cloneLanguage = $('clone-language').value;
  const cloneLanguages = config.ai_clone_languages || config.ai_voice_languages || [];
  $('clone-language').replaceChildren(...Object.entries(config.languages || {}).filter(([key]) => cloneLanguages.includes(key)).map(([key, label]) => {
    const option = node('option', label); option.value = key; return option;
  }));
  if (cloneLanguage && cloneLanguages.includes(cloneLanguage)) $('clone-language').value = cloneLanguage;
  else if (cloneLanguages.includes('vi')) $('clone-language').value = 'vi';
  $('clone-language').disabled = !$('clone-language').options.length;
  $('clone-submit').disabled = !$('clone-language').options.length;
}

function populateLibraryFilters() {
  const previous = $('library-language').value;
  const languages = new Set(voices.flatMap((voice) => voice.languages || []));
  const all = node('option', 'Tất cả quốc gia / ngôn ngữ'); all.value = 'all';
  $('library-language').replaceChildren(all, ...[...languages].map((language) => {
    const option = node('option', languageName(language)); option.value = language; return option;
  }));
  if (languages.has(previous)) $('library-language').value = previous;
  const hasGender = voices.some((voice) => genderName(voice));
  $('library-gender').hidden = !hasGender;
  if (!hasGender) $('library-gender').value = 'all';
}

function populateVoices() {
  const previous = $('voice').value;
  const choices = voices.filter((voice) => (voice.languages || []).includes($('language').value));
  $('voice').replaceChildren(...choices.map((voice) => {
    const readiness = voice.category === 'cloned' ? ` · ${cloneReadinessLabel(voice)}` : voiceReady(voice) ? '' : ' · Chưa tải';
    const option = node('option', `${voice.name} · ${engineName(voice)}${readiness}`);
    option.value = voice.id; return option;
  }));
  if (choices.some((voice) => voice.id === previous)) $('voice').value = previous;
  else {
    const preferredEngine = $('language').value === 'vi' ? 'vieneu_nano' : 'piper';
    const preferred = choices.find((voice) => voice.engine === preferredEngine && voiceReady(voice)) || choices.find(voiceReady);
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
  const ready = selectedVoiceReady(voice);
  $('clone-engine-field').hidden = !(voice?.category === 'cloned' && $('language').value === 'vi');
  $('voice-status').className = `voice-status ${ready ? 'ready' : 'missing'}`;
  const engineLabel = voice?.category === 'cloned' && $('language').value === 'vi' ? `${selectedEngine(voice) === 'vieneu_nano' ? 'Nano' : 'VieNeu'} · Nhân bản` : engineName(voice);
  $('voice-status-title').textContent = !voice ? 'Chưa có giọng phù hợp' : ready ? `${engineLabel} · Sẵn sàng sử dụng` : `${engineLabel} · Cần tải mô hình`;
  const nanoAlternative = !ready && voice?.category === 'cloned' && $('language').value === 'vi' && cloneReadyEngines(voice).vieneu_nano && selectedEngine(voice) !== 'vieneu_nano';
  $('voice-status-detail').textContent = !voice ? 'Chọn ngôn ngữ khác hoặc xóa từ khóa tìm kiếm.' : ready ? (voice.description || 'Giọng đã có trên máy.') : nanoAlternative ? 'Nhân bản Nano đã sẵn sàng. Bấm Ưu tiên tốc độ hoặc chọn Nhân bản Nano để dùng nguyên mẫu giọng này.' : config.portable || voice.engine === 'piper' ? 'Giọng này chưa sẵn sàng trong gói hiện tại. Chọn một giọng có sẵn hoặc bấm Kiểm tra lại trong Thư viện giọng.' : `Trong thư mục tool, chạy ${modelInstruction(voice, selectedEngine(voice))}, rồi bấm Kiểm tra lại ở Thư viện giọng.`;
  $('generate').disabled = !ready || submitting || importing;
  $('generate-note').textContent = !voice ? 'Cần chọn giọng hỗ trợ ngôn ngữ lời đọc.' : !ready ? 'Tải mô hình trước khi tạo giọng. Mở Hướng dẫn để xem chi tiết.' : 'Tạo trên máy · Có thể dừng và tiếp tục trong Bản thu';
  updateAcceleration();
  updateNarrationQuality();
}

function accelerationSettings() {
  return {
    nano_parallel: $('nano-parallel').value === 'auto' ? 0 : Number($('nano-parallel').value),
    nano_threads: $('nano-threads').value === 'auto' ? 0 : Number($('nano-threads').value)
  };
}

function speedPresetVoice() {
  const current = voices.find((voice) => voice.id === $('voice').value);
  if (!current) return null;
  return selectedVoiceReady(current) || (current.category === 'cloned' && $('language').value === 'vi' && cloneReadyEngines(current).vieneu_nano) ? current : null;
}

function updateAcceleration() {
  const voice = voices.find((item) => item.id === $('voice').value);
  const nano = selectedEngine(voice) === 'vieneu_nano';
  const maxWorkers = Math.max(1, Math.min(8, Number(config?.acceleration?.max_workers) || 1));
  for (const option of $('nano-parallel').options) option.disabled = option.value !== 'auto' && Number(option.value) > maxWorkers;
  if ($('nano-parallel').selectedOptions[0]?.disabled) $('nano-parallel').value = 'auto';
  for (const id of ['nano-parallel', 'nano-threads', 'nano-steps']) $(id).disabled = !nano;
  $('fast-preset').disabled = !speedPresetVoice() || submitting || benchmarking;
  $('benchmark').disabled = !selectedVoiceReady(voice) || submitting || benchmarking;
  $('benchmark').textContent = benchmarking ? 'Đang gửi mẫu đo…' : '◷ Đo tốc độ thực';
  const settings = accelerationSettings();
  $('acceleration-note').textContent = !config ? 'Đang kiểm tra cấu hình xử lý…'
    : nano ? `Nano · ${settings.nano_parallel || config.acceleration?.recommended_workers || 1} đoạn song song · ${settings.nano_threads || config.acceleration?.recommended_threads || 2} luồng CPU / đoạn. Số đoạn thực tế được giới hạn theo CPU và RAM.`
    : voice?.engine === 'piper' ? 'Piper chạy ngoại tuyến trên CPU, dùng giọng và phát âm theo quốc gia đã chọn. Không cần NVIDIA. Nút Ưu tiên tốc độ giữ nguyên giọng và ngôn ngữ.'
    : voice?.engine === 'system' ? 'Giọng Windows dùng bộ đọc đã cài trên máy. Ưu tiên tốc độ giữ nguyên giọng và chọn nhịp đọc tự nhiên.'
    : voice?.category === 'cloned' && $('language').value === 'vi' ? 'Ưu tiên tốc độ dùng nhân bản Nano và giữ mẫu giọng của bạn. Cần tải mô hình nhân bản Nano trước khi tạo.'
    : 'Ưu tiên tốc độ giữ nguyên giọng và ngôn ngữ, dùng WAV và giảm xử lý bổ sung. Mô hình quốc tế Qwen có thể chậm trên CPU; chọn Piper có sẵn nếu ưu tiên tốc độ.';
}

function applySpeedPreset() {
  const voice = speedPresetVoice();
  if (!voice) return;
  if (voice.category === 'cloned' && $('language').value === 'vi' && cloneReadyEngines(voice).vieneu_nano) $('clone-engine').value = 'nano';
  $('nano-steps').value = '4'; $('nano-parallel').value = 'auto'; $('nano-threads').value = 'auto';
  $('narration-quality').value = 'fast';
  $('paragraph-pause').value = '0'; $('delivery').value = 'natural'; $('quality').value = ['qwen', 'qwen_clone'].includes(selectedEngine(voice)) ? 'fast' : 'auto';
  $('speed').value = '1'; $('format').value = 'wav';
  $('speed-value').textContent = '1,00×'; $('delivery-note').textContent = deliveryNotes.natural;
  updateVoice();
  const ready = selectedVoiceReady(voice);
  const nano = selectedEngine(voice) === 'vieneu_nano';
  notify(`Đã giữ ${voice.category === 'cloned' ? 'mẫu giọng' : 'giọng'} ${voice.name} và ${languageName($('language').value)}; ${nano ? 'Nano 4 bước, ' : ''}đọc tự nhiên, không thêm khoảng nghỉ, xuất WAV. ${nano ? 'Ít bước có thể giảm độ tự nhiên. ' : ''}Bấm Đo tốc độ thực để kiểm tra trên máy của bạn.`, !ready);
}

function generationSettings(voice) {
  return {
    voice_id: voice.id, language: $('language').value, clone_engine: cloneEngine(),
    speed: Number($('speed').value), format: $('format').value,
    delivery: $('delivery').value, paragraph_pause: Number($('paragraph-pause').value),
    quality: $('quality').value, nano_steps: Number($('nano-steps').value),
    narration_quality: $('narration-quality').value,
    ...accelerationSettings()
  };
}

async function benchmark() {
  if (submitting || benchmarking) return;
  const voice = voices.find((item) => item.id === $('voice').value);
  if (!selectedVoiceReady(voice)) { notify('Chọn giọng và mô hình đã sẵn sàng trước khi đo.', true); return; }
  if (!$('paragraph-pause').reportValidity()) return;
  benchmarking = true; updateAcceleration(); notify('');
  try {
    const job = await post('/api/benchmark', {
      voice_id: voice.id, language: $('language').value, clone_engine: cloneEngine(),
      nano_steps: Number($('nano-steps').value), quality: $('quality').value,
      ...accelerationSettings()
    });
    setOutput(job); await refreshHistory();
    notify('Đã nhận mẫu đo bằng giọng, mô hình và số bước đã chọn, đọc tự nhiên, xuất WAV. Nội dung trong ô lời đọc được giữ nguyên.');
  } catch (error) { notify(error.message, true); }
  finally { benchmarking = false; updateAcceleration(); }
}

function updateCharacterCount() {
  const count = $('script').value.length;
  $('char-count').textContent = `${count.toLocaleString('vi-VN')} / 200.000`;
  $('char-count').classList.toggle('limit', count >= 200000);
}

function updateFormat() {
  const srt = $('script-format').value === 'srt';
  const timed = srt || scriptPreview?.has_timeline || hasTimeMarkers($('script').value);
  $('skip-timestamps').disabled = srt || (timed && $('auto-sync').checked);
  $('format-note').textContent = timed && $('auto-sync').checked ? `${srt ? 'SRT' : 'TXT'} · Tự căn theo mốc` : srt ? 'SRT · Đọc theo nhịp tự nhiên' : 'TXT · Văn bản thuần';
  $('timeline-panel').classList.toggle('sync-disabled', !$('auto-sync').checked);
}

function hasTimeMarkers(text) {
  return /(?:\d{1,3}:\d{2}(?::\d{2})?|\d+\s*phút\b)/i.test(text);
}

function timelineDuration() {
  const value = $('timeline-duration').value.trim();
  if (!value) return null;
  const cleaned = value.replace(/\s*(?:giây|seconds?|s)\s*$/i, '').replace(',', '.').trim();
  let seconds;
  if (/^\d+(?:\.\d+)?$/.test(cleaned)) seconds = Number(cleaned);
  else if (/^\d+:\d{2}(?::\d{2})?(?:\.\d{1,3})?$/.test(cleaned)) {
    const parts = cleaned.split(':').map(Number);
    if (parts.slice(1).some((part) => part >= 60)) throw new Error('Thời lượng video: phần giây/phút sau dấu : phải nhỏ hơn 60.');
    seconds = parts.reduce((total, part) => total * 60 + part, 0);
  }
  if (!(seconds > 0 && seconds <= 10800)) throw new Error('Nhập thời lượng video bằng giây hoặc dạng phút:giây / giờ:phút:giây, tối đa 3 giờ.');
  return seconds;
}

function cueTime(seconds) {
  if (seconds === null || seconds === undefined || !Number.isFinite(Number(seconds))) return 'Cần mốc kết thúc';
  const millis = Math.round(Math.max(0, Number(seconds)) * 1000);
  return `${duration(Math.floor(millis / 1000))},${String(millis % 1000).padStart(3, '0')}`;
}

function renderTimeline(result, error = '') {
  scriptPreview = result;
  const target = $('timeline-summary');
  target.classList.toggle('timeline-error', Boolean(error));
  $('timeline-cues').replaceChildren();
  const cues = Array.isArray(result?.cues) ? result.cues : [];
  $('timeline-preview').hidden = !cues.length;
  for (const cue of cues.slice(0, 8)) {
    const row = node('tr');
    row.append(node('td', `${cueTime(cue.start)} → ${cueTime(cue.end)}`), node('td', cue.text || ''));
    $('timeline-cues').append(row);
  }
  $('timeline-preview-note').textContent = cues.length > 8 ? `Đang xem 8 / ${cues.length} câu. Tất cả câu sẽ được xử lý theo mốc trong tệp.` : `${cues.length} câu có mốc thời gian.`;
  if (error) target.textContent = error;
  else if (result?.requires_total_duration) target.textContent = 'TXT chỉ có mốc bắt đầu. Nhập thời lượng video bên dưới để xác định điểm kết thúc câu cuối.';
  else if (result?.has_timeline) {
    let targetSeconds = result.timeline_seconds;
    try { targetSeconds = timelineDuration() ?? targetSeconds; } catch { /* The import error is shown after validation. */ }
    target.textContent = `${cues.length} câu · Thời lượng đích ${cueTime(targetSeconds)}${result.encoding ? ` · ${result.encoding}` : ''}. ${$('auto-sync').checked ? 'Sẽ căn từng câu theo mốc khi tạo.' : 'Đã tắt tự căn: lời đọc dùng nhịp tự nhiên.'}`;
  }
  else target.textContent = 'Văn bản chưa có mốc thời gian. Lời đọc dùng nhịp tự nhiên; SRT xuất sau khi tạo sẽ theo thời lượng đọc thực.';
  if (!error && Array.isArray(result?.warnings) && result.warnings.length) target.textContent += ` ${result.warnings.join(' ')}`;
  updateFormat();
}

function editorKey() { return `${$('script-format').value}\n${$('timeline-duration').value}\n${$('script').value}`; }

async function uploadScript(file) {
  const form = new FormData(); form.append('file', file);
  const target = timelineDuration();
  if (target !== null) form.append('timeline_seconds', String(target));
  return api('/api/scripts/import', {method: 'POST', body: form});
}

async function analyzeScript() {
  const key = editorKey();
  if (key === scriptPreviewKey && scriptPreview) return scriptPreview;
  if (scriptPreviewPromise?.key === key) return scriptPreviewPromise.promise;
  const text = $('script').value;
  if (!text.trim()) { scriptPreviewKey = key; renderTimeline(null); return null; }
  const request = ++scriptPreviewRequest;
  const promise = uploadScript(new File([text], `loi-doc.${$('script-format').value}`, {type: 'text/plain;charset=utf-8'}));
  scriptPreviewPromise = {key, promise};
  try {
    const result = await promise;
    if (request === scriptPreviewRequest && editorKey() === key) { scriptPreviewKey = key; renderTimeline(result); }
    return result;
  } catch (error) {
    if (request === scriptPreviewRequest && editorKey() === key) renderTimeline(null, error.message);
    throw error;
  } finally { if (scriptPreviewPromise?.promise === promise) scriptPreviewPromise = null; }
}

function scheduleScriptAnalysis() {
  clearTimeout(previewTimer);
  scriptPreviewKey = ''; scriptPreviewRequest += 1;
  if (!$('script').value.trim() || ($('script-format').value !== 'srt' && !hasTimeMarkers($('script').value))) { renderTimeline(null); return; }
  $('timeline-summary').textContent = 'Đang kiểm tra mốc thời gian…';
  previewTimer = setTimeout(() => analyzeScript().catch(() => {}), 700);
}

function updateNarrationQuality() {
  const voice = voices.find((item) => item.id === $('voice').value);
  const nano = selectedEngine(voice) === 'vieneu_nano' && $('language').value === 'vi';
  $('narration-quality-note').textContent = nano ? `Nano ${$('nano-steps').value} bước · Tăng số bước để ưu tiên độ mượt, nhưng xử lý lâu hơn. Cảm xúc và độ giống giọng chủ yếu phụ thuộc mẫu thu; không bảo đảm cảm xúc như người thật.` : 'Phong cách điều chỉnh nhịp đọc và khoảng nghỉ. Sắc thái cảm xúc phụ thuộc mô hình và mẫu thu; lựa chọn này tăng số bước khi dùng Nano.';
  for (const id of ['insert-laugh', 'insert-sigh', 'insert-throat']) $(id).disabled = !nano;
  $('emotion-cues-note').textContent = nano ? 'Thêm tín hiệu phi ngôn ngữ khi cần. Cảm xúc chủ yếu theo mẫu giọng 3–30 giây; Nano 16 bước mượt hơn nhưng chậm hơn. Hãy nghe thử từng câu.' : 'Các tín hiệu [cười], [thở dài], [hắng giọng] chỉ dùng với Nano tiếng Việt. Chọn Nano để thêm.';
}

function applyNarrationQuality() {
  const preset = $('narration-quality').value;
  if (preset !== 'custom') $('nano-steps').value = {fast: '4', balanced: '8', expressive: '16'}[preset];
  if (preset === 'expressive') $('quality').value = 'standard';
  else if (preset !== 'custom') $('quality').value = 'auto';
  updateNarrationQuality();
}

function insertEmotionCue(value) {
  const editor = $('script');
  const lineStart = editor.value.lastIndexOf('\n', Math.max(0, editor.selectionStart - 1)) + 1;
  const lineEnd = editor.value.indexOf('\n', editor.selectionStart);
  const line = editor.value.slice(lineStart, lineEnd === -1 ? undefined : lineEnd);
  const timestampPrefix = line.match(/^\s*[\[(][^\])]*\d{1,3}:\d{2}[^\])]*[\])]\s*/)
    || line.match(/^\s*\d{1,3}:\d{2}(?::\d{2})?(?:[,.]\d{1,3})?(?:\s*(?:-->|[-–—→])\s*\d{1,3}:\d{2}(?::\d{2})?(?:[,.]\d{1,3})?)?\s*/);
  if (($('script-format').value === 'srt' && (!line.trim() || /^\s*\d+\s*$/.test(line) || /-->|→/.test(line)))
      || (timestampPrefix && editor.selectionStart < lineStart + timestampPrefix[0].length)) {
    notify('Đặt con trỏ vào phần lời thoại, sau mốc thời gian, rồi thêm sắc thái để giữ nguyên mốc trong tệp.', true);
    editor.focus(); return;
  }
  const addition = `${value} `;
  if (editor.value.length - (editor.selectionEnd - editor.selectionStart) + addition.length > 200000) { notify('Nội dung đã đạt giới hạn 200.000 ký tự.', true); return; }
  editor.setRangeText(addition, editor.selectionStart, editor.selectionEnd, 'end');
  editor.focus(); updateCharacterCount(); scheduleScriptAnalysis();
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
  notify('Đã đưa bản thu vào hàng đợi để tiếp tục.');
}

function addJobControls(container, job) {
  if (job.status === 'done') addExportButtons(container, job);
  if (activeStatuses.has(job.status)) {
    const stop = makeButton(job.status === 'cancelling' ? 'Đang dừng…' : '■ Dừng tạo', () => cancelJob(job));
    stop.disabled = job.status === 'cancelling'; container.append(stop);
  }
  if (['error', 'cancelled'].includes(job.status)) container.append(makeButton('▷ Tiếp tục bản thu', () => resumeJob(job)));
}

function setOutput(job) {
  selectedJob = job;
  const signature = JSON.stringify([job.id, job.status, job.progress, job.phase, job.error, job.audio_seconds, job.duration_limited, job.speed_report, job.benchmark, job.sync_report]);
  if (outputSignature === signature) return;
  outputSignature = signature;
  const progress = Math.max(0, Math.min(100, Number(job.progress) || 0));
  $('output-heading').textContent = {
    queued: 'Bản thu đã vào hàng đợi', running: 'Đang tạo giọng nói…', cancelling: 'Đang dừng bản thu…',
    cancelled: 'Đã dừng · Có thể tiếp tục', error: 'Bản thu cần được kiểm tra', done: 'Bản thu đã sẵn sàng'
  }[job.status] || 'Bản thu của bạn';
  if (job.benchmark) $('output-heading').textContent = job.status === 'done' ? 'Đã đo tốc độ trên mẫu âm thanh thật' : activeStatuses.has(job.status) ? 'Đang tạo mẫu đo tốc độ…' : 'Mẫu đo tốc độ cần được kiểm tra';
  if (job.status === 'done' && job.speed_report?.hour_target_verified) $('output-heading').textContent = 'Đã tạo đủ 1 giờ âm thanh trong 2 phút';
  $('output-status').hidden = false;
  $('output-status').className = `status-badge ${job.status}`;
  $('output-status').textContent = `${statusNames[job.status] || job.status}${activeStatuses.has(job.status) ? ` · ${progress}%` : ''}`;
  $('output-detail').textContent = `${job.voice_name || 'Giọng đọc'} · ${languageName(job.language)} · ${duration(job.audio_seconds)}${job.phase ? ` · ${job.phase}` : ''}`;
  $('output-progress').hidden = !activeStatuses.has(job.status);
  $('output-progress').value = progress;
  const warning = job.error || (job.duration_limited ? 'Đã đạt giới hạn thời lượng. Phần nội dung còn lại chưa được đọc; chia lời đọc thủ công hoặc tăng giới hạn (tối đa 180 phút) để tạo lại.' : '');
  $('output-warning').textContent = warning; $('output-warning').hidden = !warning;
  const done = job.status === 'done';
  $('output-audio').hidden = !done;
  if (done) {
    const url = `/api/audio/${encodeURIComponent(job.id)}`;
    if ($('output-audio').getAttribute('src') !== url) $('output-audio').src = url;
  } else if ($('output-audio').hasAttribute('src')) {
    $('output-audio').pause(); $('output-audio').removeAttribute('src'); $('output-audio').load();
  }
  $('output-actions').replaceChildren(); addJobControls($('output-actions'), job);
  const sync = job.sync_report;
  $('sync-report').hidden = !sync;
  if (sync) {
    const complete = done && sync.complete === true && Number(sync.matched_cues) === Number(sync.total_cues);
    $('sync-report').classList.toggle('incomplete', !complete);
    $('sync-report').textContent = `${complete ? 'Đã căn khớp mốc thời gian' : activeStatuses.has(job.status) ? 'Đang kiểm tra đồng bộ' : 'Chưa căn khớp toàn bộ'} · ${Number(sync.matched_cues) || 0}/${Number(sync.total_cues) || 0} câu · Đích ${cueTime(sync.target_seconds)} · Bản thu ${cueTime(sync.actual_seconds)} · Sai lệch lớn nhất ${Number(sync.max_error_ms || 0).toLocaleString('vi-VN', {maximumFractionDigits: 3})} ms. ${job.format === 'mp3' ? 'MP3 có thể hiển thị thêm đệm nén ở một số phần mềm. Dùng WAV để ghép video theo mẫu âm thanh chính xác.' : 'Tải WAV cùng SRT để đặt vào video theo mốc gốc.'}`;
  }
  const report = job.speed_report;
  $('speed-report').hidden = !done || !report?.realtime_multiplier;
  if (!report?.realtime_multiplier) $('speed-report').textContent = '';
  else if (report.hour_target_verified) {
    $('speed-report').textContent = `Đã tạo thực tế ${duration(report.measurement_audio_seconds)} âm thanh trong ${Number(report.measurement_elapsed_seconds).toLocaleString('vi-VN')} giây xử lý · ${Number(report.realtime_multiplier).toLocaleString('vi-VN')}×. Đã đạt mục tiêu 1 giờ âm thanh trong 2 phút trên máy và bản thu này. Tốc độ trên máy khác hoặc nội dung khác có thể thay đổi.`;
  } else {
    $('speed-report').textContent = `Tốc độ đo trên ${job.benchmark ? 'mẫu' : 'bản thu'} này: ${Number(report.realtime_multiplier).toLocaleString('vi-VN')}× · ${Number(report.measurement_audio_seconds).toLocaleString('vi-VN')} giây âm thanh / ${Number(report.measurement_elapsed_seconds).toLocaleString('vi-VN')} giây xử lý.${Number(report.estimated_hour_seconds) > 0 ? ` Ước tính tạo 1 giờ âm thanh: ${duration(report.estimated_hour_seconds)}. ${report.target_30x_met_on_sample ? 'Đạt' : 'Chưa đạt'} mục tiêu 2 phút / 1 giờ trên mẫu đo này.` : ''} Kết quả nội dung dài có thể khác; không phải cam kết tốc độ.`;
  }
}

async function generate() {
  if (submitting) return;
  if (!$('script').value.trim()) { notify('Hãy nhập nội dung cần đọc.', true); $('script').focus(); return; }
  if ($('script').value.length > 200000) { notify('Mỗi lần tạo nhận tối đa 200.000 ký tự.', true); return; }
  for (const id of ['max-minutes', 'paragraph-pause']) if (!$(id).reportValidity()) return;
  const voice = voices.find((item) => item.id === $('voice').value);
  if (!selectedVoiceReady(voice)) { notify('Chọn một giọng và mô hình đã sẵn sàng hoặc tải mô hình trước.', true); return; }
  submitting = true; updateVoice(); notify('');
  try {
    clearTimeout(previewTimer);
    const sync = $('auto-sync').checked;
    const target = timelineDuration();
    let text = $('script').value;
    let inputFormat = $('script-format').value;
    let parsed = null;
    if (sync && (inputFormat === 'srt' || hasTimeMarkers(text))) {
      parsed = await analyzeScript();
      if (parsed?.requires_total_duration) throw new Error('Nhập thời lượng video để căn điểm kết thúc câu cuối trong TXT, rồi tạo lại.');
      if (parsed?.has_timeline && parsed.text.length <= 200000) { text = parsed.text; inputFormat = parsed.input_format || 'srt'; }
    }
    const job = await post('/api/speech', {
      ...generationSettings(voice), text,
      input_format: inputFormat, skip_timestamps: $('skip-timestamps').checked,
      timing_mode: sync ? (inputFormat === 'srt' ? 'exact' : 'auto') : 'natural',
      timeline_seconds: target ?? (parsed?.has_timeline ? parsed.timeline_seconds : null),
      max_minutes: Number($('max-minutes').value)
    });
    setOutput(job); notify('Đã nhận nội dung. Bạn có thể theo dõi bản thu ở bên dưới.');
    await refreshHistory();
  } catch (error) { notify(error.message, true); }
  finally { submitting = false; updateVoice(); }
}

async function importScript(file) {
  if (!file) return;
  if (!/\.(txt|srt)$/i.test(file.name)) throw new Error('Chọn tệp có đuôi .txt hoặc .srt.');
  if (file.size > 2 * 1024 * 1024) throw new Error('Tệp văn bản không được vượt quá 2 MB.');
  if (importing) return;
  if ($('script').value.trim() && !window.confirm('Thay nội dung đang nhập bằng nội dung trong tệp?')) return;
  clearTimeout(previewTimer); scriptPreviewRequest += 1;
  importing = true; $('import-script').disabled = true; $('import-script').textContent = 'Đang nhập tệp…'; updateVoice();
  notify(`Đang nhập ${file.name} và kiểm tra mã hóa, mốc thời gian…`);
  try {
    const result = await uploadScript(file);
    const expanded = typeof result.text === 'string' && result.text.length > 200000;
    const text = expanded ? result.source_text : result.text;
    if (typeof text !== 'string' || !text.trim()) throw new Error('Tệp chưa có nội dung để đọc.');
    if (text.length > 200000) throw new Error('Tệp vượt quá 200.000 ký tự. Hãy chia nội dung thành các phần trước khi nhập.');
    $('script').value = text; $('script-format').value = (expanded ? result.source_input_format : result.input_format) || (/\.srt$/i.test(file.name) ? 'srt' : 'txt');
    $('auto-sync').checked = true;
    scriptPreviewKey = editorKey(); renderTimeline(result); updateCharacterCount();
    notify(`Đã nhập ${text.length.toLocaleString('vi-VN')} ký tự từ ${file.name}${result.has_timeline ? ' và giữ mốc thời gian' : ''}.${result.requires_total_duration ? ' Nhập thời lượng video để căn câu cuối.' : ''}${result.warnings?.length ? ` ${result.warnings.join(' ')}` : ''}`);
  } finally {
    importing = false; $('import-script').disabled = false; $('import-script').textContent = '↑ Nhập TXT / SRT'; updateVoice();
  }
}

async function exportScript(extension) {
  let text = $('script').value;
  let format = $('script-format').value;
  if (!text.trim()) throw new Error('Chưa có nội dung để xuất.');
  if (format === 'srt' || hasTimeMarkers(text)) {
    const parsed = await analyzeScript();
    if (parsed?.requires_total_duration) throw new Error('Nhập thời lượng video để xác định mốc kết thúc câu cuối trước khi xuất.');
    if (parsed?.has_timeline) {
      const clock = (seconds) => cueTime(seconds).replace(/^(\d):/, '0$1:');
      const escapeText = (value) => String(value).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      const output = extension === 'srt' ? parsed.text : `${parsed.cues.map((cue) => `[${clock(cue.start)} --> ${clock(cue.end)}] ${escapeText(cue.text)}`).join('\n\n')}\n`;
      downloadBlob(new Blob([output], {type: 'text/plain;charset=utf-8'}), `loi-doc.${extension}`); return;
    }
  }
  if (extension === 'srt' && format === 'txt') {
    const job = history.find((item) => item.status === 'done' && item.input_format !== 'srt' && item.text.trim() === text.trim());
    if (!job) throw new Error('Tạo giọng hoàn tất với nội dung này trước khi xuất SRT để có mốc thời gian lời đọc thực.');
    await downloadExport(job, extension); return;
  }
  const result = await post('/api/scripts/convert', {text, input_format: format, output_format: extension, preserve_timing: true});
  downloadBlob(new Blob([result.text], {type: 'text/plain;charset=utf-8'}), `loi-doc.${extension}`);
}

function renderLibrary() {
  const query = searchText($('voice-search').value.trim());
  const filter = $('library-filter').value;
  const language = $('library-language').value;
  const gender = $('library-gender').value;
  const entries = voices.filter((voice) => !query || voiceSearchText(voice).includes(query))
    .filter((voice) => language === 'all' || (voice.languages || []).includes(language))
    .filter((voice) => gender === 'all' || voice.gender === gender)
    .filter((voice) => filter === 'all' || (filter === 'ready' && libraryVoiceReady(voice)) || (filter === 'cloned' && voice.category === 'cloned') || (filter === 'system' && voice.engine === 'system'));
  $('library-count').textContent = `${entries.length} / ${voices.length} giọng · Tìm theo tên, quốc gia hoặc ngôn ngữ`;
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
    if (genderName(voice)) tags.append(node('span', genderName(voice), 'small-tag'));
    for (const language of (voice.languages || []).slice(0, 2)) tags.append(node('span', languageName(language), 'small-tag'));
    if ((voice.languages || []).length > 2) tags.append(node('span', `+${voice.languages.length - 2} ngôn ngữ`, 'small-tag'));
    card.append(tags);
    const ready = libraryVoiceReady(voice);
    const readinessLabel = voice.category === 'cloned' ? `${ready ? '●' : '○'} ${cloneReadinessLabel(voice)}` : ready ? '● Sẵn sàng sử dụng' : voice.engine === 'piper' ? '○ Mô hình Piper chưa sẵn sàng' : `○ Chưa tải · ${modelInstruction(voice)}`;
    card.append(node('p', readinessLabel, `readiness ${ready ? 'ready' : 'missing'}`));
    if (voice.category === 'cloned') {
      const audio = node('audio'); audio.controls = true; audio.preload = 'none'; audio.src = `/api/voices/${encodeURIComponent(voice.id)}/sample`;
      audio.setAttribute('aria-label', `Nghe mẫu giọng ${voice.name}`); card.append(audio);
    }
    const controls = node('div', null, 'button-row');
    controls.append(makeButton('Chọn giọng →', async () => {
      $('language-search').value = ''; populateLanguages();
      const language = (voice.languages || []).find((value) => [...$('language').options].some((option) => option.value === value));
      if (!language) throw new Error('Chưa có ngôn ngữ phù hợp cho giọng này.');
      $('language').value = language; populateVoices(); $('voice').value = voice.id; updateVoice();
      showView('create'); $('script').focus();
      if (!selectedVoiceReady(voice) && voice.category === 'cloned' && language === 'vi' && cloneReadyEngines(voice).vieneu_nano) {
        notify('Nhân bản Nano đã sẵn sàng cho mẫu giọng này. Bấm Ưu tiên tốc độ hoặc chọn Nhân bản Nano để sử dụng.');
      } else if (!selectedVoiceReady(voice)) {
        notify(`Giọng này cần mô hình đang chọn. Chạy ${modelInstruction(voice, selectedEngine(voice))} trong thư mục tool rồi kiểm tra lại.`, true);
      } else notify('');
    }));
    if (ready && voice.category !== 'cloned') controls.append(makeButton('Tạo mẫu nghe thử', async () => {
      $('language-search').value = ''; populateLanguages();
      const language = (voice.languages || []).find((value) => [...$('language').options].some((option) => option.value === value));
      if (!language) throw new Error('Chưa có ngôn ngữ phù hợp cho giọng này.');
      $('language').value = language; populateVoices(); $('voice').value = voice.id; updateVoice();
      showView('create'); await benchmark();
      $('output-heading').scrollIntoView({block: 'center', behavior: 'auto'});
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
  const title = node('div'); title.append(node('h2', `${job.benchmark ? 'Đo tốc độ · ' : ''}${job.voice_name || 'Bản thu'}`), node('p', `${languageName(job.language)} · ${new Date(job.created_at).toLocaleString('vi-VN')} · ${(job.format || 'wav').toUpperCase()}`, 'history-meta'));
  heading.append(title, node('span', statusNames[job.status] || job.status, `status-badge ${job.status}`));
  card.append(heading, node('p', (job.text || '').length > 220 ? `${job.text.slice(0, 220)}…` : job.text, 'history-excerpt'));
  card.append(node('p', `${Number(job.progress) || 0}% · ${duration(job.audio_seconds)}${job.completed !== undefined && job.total ? ` · ${job.completed}/${job.total} đoạn xử lý` : ''}${job.phase ? ` · ${job.phase}` : ''}`, 'field-note'));
  if (activeStatuses.has(job.status)) {
    const progress = node('progress'); progress.max = 100; progress.value = Number(job.progress) || 0; progress.setAttribute('aria-label', 'Tiến độ bản thu'); card.append(progress);
  }
  if (job.error) card.append(node('p', job.error, 'history-error'));
  if (job.duration_limited) card.append(node('p', 'Đã đạt giới hạn thời lượng; còn nội dung chưa đọc.', 'history-error'));
  if (job.sync_report) card.append(node('p', `${job.sync_report.complete ? 'Đã căn mốc' : 'Chưa căn xong'} · ${Number(job.sync_report.matched_cues) || 0}/${Number(job.sync_report.total_cues) || 0} câu · ${cueTime(job.sync_report.actual_seconds)} / ${cueTime(job.sync_report.target_seconds)}`, 'field-note'));
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
  for (const id of ['output-status', 'output-progress', 'output-warning', 'output-audio', 'speed-report', 'sync-report']) $(id).hidden = true;
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
    const signature = JSON.stringify([job.status, job.progress, job.phase, job.completed, job.audio_seconds, job.error, job.duration_limited, job.sync_report]);
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
  const modelEntries = Object.entries(config.models || {}).filter(([key]) => !config.portable || !['qwen', 'qwen_clone'].includes(key));
  for (const [key, ready] of [['vieneu_nano', config.nano_ready], ...modelEntries]) target.append(node('p', `${ready ? '●' : '○'} ${key}: ${ready ? 'Đã tải' : 'Chưa tải'}`));
  const piperVoices = voices.filter((voice) => voice.engine === 'piper' && voiceReady(voice));
  if (piperVoices.length) target.append(node('p', `● Piper: ${piperVoices.length} giọng có sẵn · ${new Set(piperVoices.flatMap((voice) => voice.languages || [])).size} lựa chọn ngôn ngữ / quốc gia · CPU ngoại tuyến.`));
  target.append(node('p', `${config.nano_clone_ready ? '●' : '○'} Nhân bản Nano: ${config.nano_clone_ready ? 'Đã tải' : 'Chưa tải · TAI_GIONG_NHAN_BAN_NHANH.bat'}`));
  if (config.acceleration) target.append(node('p', `Nano tự động: ${config.acceleration.recommended_workers || 1} đoạn cùng lúc · ${config.acceleration.recommended_threads || 2} luồng CPU mỗi đoạn.`));
  target.append(node('p', 'Giọng hệ thống Windows có thể dùng ngay khi đã được cài trong hệ điều hành.'));
}

async function refreshVoices() {
  const results = await Promise.all([api('/api/config'), api('/api/voices')]);
  config = results[0]; voices = results[1].voices || [];
  if (!defaultsApplied) {
    $('clone-engine').value = config.default_clone_engine || 'auto';
    $('nano-steps').value = String(config.default_nano_steps || 4);
    $('narration-quality').value = config.default_narration_quality || 'balanced';
    $('paragraph-pause').value = String(config.default_paragraph_pause ?? 0);
    applyNarrationQuality();
    defaultsApplied = true;
  }
  populateLanguages(); populateVoices(); populateLibraryFilters(); renderLibrary(); renderModelStatus();
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
$('language-search').addEventListener('input', () => { populateLanguages(); populateVoices(); });
$('voice').addEventListener('change', updateVoice);
$('clone-engine').addEventListener('change', updateVoice);
$('script').addEventListener('input', () => { updateCharacterCount(); scheduleScriptAnalysis(); });
$('script-format').addEventListener('change', () => { updateFormat(); scheduleScriptAnalysis(); });
$('auto-sync').addEventListener('change', () => renderTimeline(scriptPreview));
$('timeline-duration').addEventListener('input', scheduleScriptAnalysis);
$('narration-quality').addEventListener('change', applyNarrationQuality);
for (const id of ['nano-steps', 'quality']) $(id).addEventListener('change', () => { $('narration-quality').value = 'custom'; updateNarrationQuality(); });
for (const [id, value] of [['insert-laugh', '[cười]'], ['insert-sigh', '[thở dài]'], ['insert-throat', '[hắng giọng]']]) $(id).addEventListener('click', () => insertEmotionCue(value));
$('speed').addEventListener('input', () => { $('speed-value').textContent = `${Number($('speed').value).toLocaleString('vi-VN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}×`; });
$('delivery').addEventListener('change', () => { $('delivery-note').textContent = deliveryNotes[$('delivery').value]; });
$('generate').addEventListener('click', generate);
$('fast-preset').addEventListener('click', applySpeedPreset);
$('benchmark').addEventListener('click', benchmark);
for (const id of ['nano-parallel', 'nano-threads']) $(id).addEventListener('change', updateAcceleration);
$('import-script').addEventListener('click', () => $('script-file').click());
$('script-file').addEventListener('change', async () => {
  try { await importScript($('script-file').files[0]); } catch (error) { notify(error.message, true); }
  finally { $('script-file').value = ''; }
});
const editorCard = document.querySelector('.editor-card');
editorCard.addEventListener('dragover', (event) => {
  if (!event.dataTransfer?.types.includes('Files')) return;
  event.preventDefault(); event.dataTransfer.dropEffect = 'copy'; editorCard.classList.add('drag-over');
});
editorCard.addEventListener('dragleave', (event) => { if (!editorCard.contains(event.relatedTarget)) editorCard.classList.remove('drag-over'); });
editorCard.addEventListener('drop', async (event) => {
  if (!event.dataTransfer?.files.length) return;
  event.preventDefault(); editorCard.classList.remove('drag-over');
  try {
    if (event.dataTransfer.files.length !== 1) throw new Error('Mỗi lần hãy kéo thả một tệp TXT hoặc SRT.');
    await importScript(event.dataTransfer.files[0]);
  } catch (error) { notify(error.message, true); }
  finally { $('script-file').value = ''; }
});
for (const extension of ['txt', 'srt']) $(`export-${extension}`).addEventListener('click', async () => {
  try { await exportScript(extension); } catch (error) { notify(error.message, true); }
});
$('voice-search').addEventListener('input', renderLibrary);
$('library-filter').addEventListener('change', renderLibrary);
$('library-language').addEventListener('change', renderLibrary);
$('library-gender').addEventListener('change', renderLibrary);
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
    if (config.portable) {
      const steps = document.querySelector('.help-steps');
      steps.replaceChildren();
      for (const message of [
        'Giải nén toàn bộ ZIP, mở MO_TOOL.bat. Python, FFmpeg, mô hình tiếng Việt và các giọng Piper quốc tế trong thư viện đã có sẵn; không cần cài đặt hoặc tải thêm.',
        'Chọn quốc gia / ngôn ngữ rồi chọn giọng sẵn sàng. Với mẫu giọng cá nhân tiếng Việt, chế độ Tự động ưu tiên Nano 4 bước khi đã sẵn sàng; nghe thử để kiểm tra độ giống giọng.',
        'Nhập hoặc kéo thả TXT/SRT, tối đa 200.000 ký tự. Giữ nguyên mốc thời gian và bật Tự căn lời đọc để khớp video. TXT chỉ có mốc bắt đầu cần nhập thời lượng video cho câu cuối.',
        'Chọn Cân bằng hoặc Ưu tiên tự nhiên để tăng số bước Nano; tín hiệu [cười], [thở dài], [hắng giọng] chỉ dùng với Nano tiếng Việt. Nghe thử để kiểm tra sắc thái của mẫu giọng.',
        'Tạo xong, kiểm tra báo cáo căn mốc rồi tải WAV cùng SRT để ghép video. MP3 có thể hiển thị thêm đệm nén trong một số trình biên tập. Giữ cửa sổ tool mở khi sử dụng.',
        'Sao lưu app/.data trước khi cập nhật hoặc xóa tool. Giọng có sẵn đa ngôn ngữ và nhân bản tiếng Việt là các chức năng riêng; công cụ không tự dịch văn bản.'
      ]) steps.append(node('li', message));
      $('help-speed').textContent = 'Ưu tiên tốc độ: giữ nguyên giọng và ngôn ngữ đã chọn, dùng WAV, đọc tự nhiên và không thêm khoảng nghỉ. Giọng nhân bản tiếng Việt dùng Nano 4 bước khi mô hình đã sẵn sàng. Giọng Piper quốc tế chạy nhanh trên CPU; không cần NVIDIA. Nano 4 bước có thể giảm độ tự nhiên; cần nghe thử.';
      $('privacy-note').textContent = 'Nội dung và bản thu được lưu trên máy. Các giọng có sẵn trong gói Portable hoạt động ngoại tuyến.';
    }
    if (history[0]) setOutput(history[0]);
    if (!voices.some(libraryVoiceReady)) notify('Phòng thu đã mở. Chưa có giọng sẵn sàng; xem Hướng dẫn để tải mô hình trước khi tạo âm thanh.');
  } catch (error) { notify(error.message, true); setConnection(false); connectionFailed = true; }
  pollTimer = setTimeout(poll, 3000);
}
init();
