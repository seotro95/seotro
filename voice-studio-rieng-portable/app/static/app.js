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
let appliedCalibrationId = '';
let appliedRenderEngine = null;
let speedSummary = null;
let historyVisibleCount = 20;
let characterCountFrame;
let lastSavedRenderPreferences = '';
let renderStorageAvailable = true;
const historyNodes = new Map();
const renderPreferenceKey = 'voice-studio.render-settings.v1';
const renderModes = new Set(['fast', 'balanced', 'quality']);
const renderEngines = new Set(['vieneu_nano', 'vieneu', 'voxcpm']);
const resourceProfiles = new Set(['maximum', 'smooth', 'light']);
let renderPreferences = readRenderPreferences();

function readRenderPreferences() {
  try {
    const saved = JSON.parse(localStorage.getItem(renderPreferenceKey));
    if (saved?.schema_version === 1 && saved.tuning && typeof saved.tuning === 'object' && !Array.isArray(saved.tuning)) {
      lastSavedRenderPreferences = JSON.stringify(saved);
      return saved;
    }
  } catch { /* Restricted browser storage must not prevent local synthesis. */ }
  return {schema_version: 1, tuning: {}};
}

function saveRenderPreferences() {
  if (!renderSettingsInitialized) return;
  renderPreferences.mode = $('render-mode').value;
  renderPreferences.language = $('language').value;
  renderPreferences.voice_id = $('voice').value;
  renderPreferences.resource_profile = $('resource-profile').value;
  renderPreferences.international_precision = $('international-precision').value;
  const serialized = JSON.stringify(renderPreferences);
  if (!renderStorageAvailable || serialized === lastSavedRenderPreferences) return;
  try { localStorage.setItem(renderPreferenceKey, serialized); lastSavedRenderPreferences = serialized; }
  catch { renderStorageAvailable = false; /* Keep using session settings when storage is unavailable. */ }
}

function renderTuningKey(engine, mode) {
  const base = `${$('resource-profile').value}:${engine}:${mode}`;
  return engine === 'voxcpm' ? `${base}:${$('international-precision').value}` : base;
}

function savedRenderTuning(engine, mode) {
  const profile = $('resource-profile').value;
  const legacyCompatible = engine !== 'voxcpm' || $('international-precision').value === 'fp32';
  const saved = renderPreferences.tuning[renderTuningKey(engine, mode)]
    || (legacyCompatible ? renderPreferences.tuning[`${profile}:${engine}:${mode}`] : null)
    || (legacyCompatible && profile === 'smooth' ? renderPreferences.tuning[`${engine}:${mode}`] : null);
  if (!saved || typeof saved !== 'object' || Array.isArray(saved)) return {};
  const tuning = {};
  for (const [key, maximum] of [['nano_parallel', engine === 'voxcpm' ? 8 : 32], ['nano_threads', 8]]) {
    if (Number.isInteger(saved[key]) && saved[key] >= 1 && saved[key] <= maximum) tuning[key] = saved[key];
  }
  if ([4, 8, 16].includes(saved.nano_steps)) tuning.nano_steps = saved.nano_steps;
  if ([4, 8, 10].includes(saved.voxcpm_steps)) tuning.voxcpm_steps = saved.voxcpm_steps;
  if (['ffmpeg', 'wsola'].includes(saved.audio_fit_backend)) tuning.audio_fit_backend = saved.audio_fit_backend;
  if (['auto', 'standard', 'fast'].includes(saved.quality)) tuning.quality = saved.quality;
  return tuning;
}

function rememberRenderTuning() {
  const voice = voices.find((item) => item.id === $('voice').value);
  if (renderEngines.has(voice?.engine)) {
    const tuning = {nano_parallel: Number($('nano-parallel').value), nano_threads: Number($('nano-threads').value),
      audio_fit_backend: $('audio-fit-backend').value, quality: $('quality').value};
    if (voice.engine === 'vieneu_nano') tuning.nano_steps = Number($('nano-steps').value);
    if (voice.engine === 'voxcpm') tuning.voxcpm_steps = Number($('voxcpm-steps').value);
    renderPreferences.tuning[renderTuningKey(voice.engine, $('render-mode').value)] = tuning;
  }
  saveRenderPreferences();
  updateRenderNote();
}

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
  if (view === 'history') renderHistory();
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
  if (voice?.engine === 'voxcpm') return 'TAI_GIONG_DA_NGON_NGU.bat';
  return 'TAI_GIONG_QUOC_TE.bat';
}

function voiceSetupMessage(voice) {
  return `${voice?.missing_reason || 'Giọng này cần mô hình.'} Trong thư mục tool, chạy ${modelInstruction(voice)}, rồi bấm Kiểm tra lại ở Thư viện giọng.`;
}

function languageName(language) { return config?.languages?.[language] || language || 'Chưa rõ ngôn ngữ'; }
function engineName(voice) {
  return {vieneu_nano: 'Nano', vieneu: 'Turbo', voxcpm: 'Giọng mẫu đa ngôn ngữ', qwen: 'Qwen', qwen_clone: 'Qwen · Nhân bản', system: 'Hệ thống Windows'}[voice?.engine] || voice?.engine || 'AI';
}

function cpuVoice(voice) { return renderEngines.has(voice?.engine); }
function calibrationVoice(voice) { return ['vieneu_nano', 'vieneu'].includes(voice?.engine); }

function benchmarkSupported(voice) {
  const language = $('language').value;
  if (Array.isArray(config?.benchmark_languages)) return config.benchmark_languages.includes(language);
  if (voice?.engine === 'voxcpm') return (config?.ai_voice_languages || []).includes(language);
  if (voice?.engine === 'vieneu') return ['vi', 'en-US', 'en-GB'].includes(language);
  return language === 'vi';
}

function renderingPresets(voice) {
  if (voice?.engine === 'voxcpm' && $('international-precision').value === 'int8') {
    const compact = config?.voxcpm_int8_rendering_presets_by_resource?.[$('resource-profile').value];
    if (compact) return compact;
  }
  const profilePresets = config?.rendering_presets_by_resource?.[$('resource-profile').value]?.[voice?.engine];
  if (profilePresets) return profilePresets;
  if (voice?.engine === 'voxcpm') return config?.voxcpm_rendering_presets;
  return voice?.engine === 'vieneu' ? config?.turbo_rendering_presets : config?.rendering_presets;
}

function populateResourceProfiles() {
  const selected = $('resource-profile').value;
  if (Array.isArray(config?.resource_profiles)) {
    const options = config.resource_profiles.filter((profile) => resourceProfiles.has(profile.id));
    if (options.length) {
      $('resource-profile').replaceChildren(...options.map((profile) => {
        const option = node('option', profile.name || profile.id);
        option.value = profile.id;
        return option;
      }));
      $('resource-profile').value = options.some((profile) => profile.id === selected) ? selected
        : options.some((profile) => profile.id === 'smooth') ? 'smooth' : options[0].id;
    }
  }
  updateResourceNote();
}

function updateResourceNote() {
  const descriptions = {
    maximum: 'Dùng nhiều CPU hơn để hoàn thành nhanh; máy có thể kém mượt khi làm việc khác.',
    smooth: 'Ưu tiên máy phản hồi mượt trong khi tạo giọng. Có thể mất thêm thời gian so với dùng tối đa CPU.',
    light: 'Ít tác vụ và luồng hơn để giảm RAM và tải CPU. Tốc độ hoàn thành có thể chậm hơn.'
  };
  const profile = config?.resource_profiles?.find((item) => item.id === $('resource-profile').value);
  $('resource-profile-note').textContent = profile?.description || descriptions[$('resource-profile').value] || '';
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
  if (cpuVoice(current)) {
    note += ` Đang giữ giọng ${current.name} · ${engineName(current)}: ${$('nano-parallel').value} tác vụ × ${$('nano-threads').value} luồng CPU.`;
    if (current.engine === 'vieneu' && config?.int8_cpu === false) note += ' CPU này không hỗ trợ VNNI; Turbo dùng FP32. Có thể chuyển sang Nano để đo so sánh.';
    if (current.engine === 'voxcpm') note += ` ${$('voxcpm-steps').value} bước tạo giọng · ${$('international-precision').value.toUpperCase()}. Ít bước hơn có thể giảm độ tự nhiên; đo và nghe mẫu trước khi tạo bản dài.`;
  } else if ($('render-mode').value === 'fast' && current) {
    note += ` Đang giữ giọng ${current.name} · ${engineName(current)}. Giọng này dùng cơ chế xử lý riêng của mô hình.`;
  }
  $('render-note').textContent = note;
  const nano = fastNanoVoice();
  $('choose-nano').disabled = !nano || submitting;
  $('choose-nano').title = nano ? `Chuyển sang ${nano.name}, áp dụng ưu tiên tốc độ và tạo mẫu đo. Kịch bản đang nhập được giữ nguyên.` : 'Cần chọn tiếng Việt và tải giọng Nano trước khi sử dụng.';
}

function applyRenderMode(mode, {useSaved = true, remember = true} = {}) {
  $('render-mode').value = mode;
  const voice = voices.find((item) => item.id === $('voice').value);
  const key = renderTuningKey(voice?.engine, mode);
  if (!useSaved) {
    delete renderPreferences.tuning[key];
    if (voice?.engine !== 'voxcpm' || $('international-precision').value === 'fp32') {
      delete renderPreferences.tuning[`${$('resource-profile').value}:${voice?.engine}:${mode}`];
      if ($('resource-profile').value === 'smooth') delete renderPreferences.tuning[`${voice?.engine}:${mode}`];
    }
  }
  const preset = {...(renderingPresets(voice)?.[mode] || {}), ...(useSaved ? savedRenderTuning(voice?.engine, mode) : {})};
  const changedEngine = voice?.engine !== appliedRenderEngine;
  appliedRenderEngine = voice?.engine || null;
  $('nano-steps').value = String(preset.nano_steps || {fast: 4, balanced: 8, quality: 16}[mode] || 8);
  $('voxcpm-steps').value = String(preset.voxcpm_steps || {fast: 4, balanced: 8, quality: 10}[mode] || 8);
  $('nano-parallel').value = String(Math.max(1, Math.min(voice?.engine === 'voxcpm' ? 8 : 32, Number(preset.nano_parallel) || 1)));
  $('nano-threads').value = String(Math.max(1, Math.min(8, Number(preset.nano_threads) || 2)));
  $('audio-fit-backend').value = preset.audio_fit_backend || (mode === 'fast' ? 'wsola' : 'ffmpeg');
  if (preset.quality) $('quality').value = preset.quality;
  else if (changedEngine || !useSaved) $('quality').value = 'auto';
  if (remember) saveRenderPreferences();
  updateRenderNote();
}

function applyResourceBudget() {
  const voice = voices.find((item) => item.id === $('voice').value);
  const preset = renderingPresets(voice)?.[$('render-mode').value];
  if (preset) {
    $('nano-parallel').value = String(Math.max(1, Math.min(voice?.engine === 'voxcpm' ? 8 : 32, Number(preset.nano_parallel) || 1)));
    $('nano-threads').value = String(Math.max(1, Math.min(8, Number(preset.nano_threads) || 1)));
  }
  // A resource choice changes CPU/RAM use. Keep the selected voice, sampling
  // steps and fitting method, which also affect pronunciation and timing.
  rememberRenderTuning();
}

async function inspectMachine() {
  const button = $('inspect-machine');
  button.disabled = true; button.textContent = 'Đang kiểm tra máy…';
  try {
    const info = await api('/api/system-info');
    if (info.rendering_presets && config) config.rendering_presets = info.rendering_presets;
    if (info.turbo_rendering_presets && config) config.turbo_rendering_presets = info.turbo_rendering_presets;
    if (info.voxcpm_rendering_presets && config) config.voxcpm_rendering_presets = info.voxcpm_rendering_presets;
    if (info.rendering_presets_by_resource && config) config.rendering_presets_by_resource = info.rendering_presets_by_resource;
    if (info.voxcpm_int8_rendering_presets_by_resource && config) config.voxcpm_int8_rendering_presets_by_resource = info.voxcpm_int8_rendering_presets_by_resource;
    const gpuNames = Array.isArray(info.nvidia_gpus) ? info.nvidia_gpus : [];
    const rows = [
      ['Bộ xử lý', info.cpu || 'Chưa xác định'],
      ['Lõi CPU vật lý', info.physical_cores || 'Chưa xác định'],
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
  for (const voice of voices) for (const language of voice.languages || []) available.add(language);
  const labels = new Map(Object.entries(config.languages || {}));
  for (const language of available) if (!labels.has(language)) labels.set(language, languageName(language));
  const options = [...labels].filter(([key]) => available.has(key));
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
    const option = node('option', `${voice.name}${voice.category === 'reference' && voice.is_default ? ' · Mặc định của bạn' : ''} · ${engineName(voice)}${voiceReady(voice) ? '' : ' · Chưa tải'}`);
    option.value = voice.id; return option;
  }));
  if (choices.some((voice) => voice.id === previous)) $('voice').value = previous;
  else {
    const defaults = choices.filter((voice) => voice.category === 'reference' && voice.is_default);
    const vietnameseNano = $('language').value === 'vi' && choices.find((voice) => voice.engine === 'vieneu_nano' && voiceReady(voice));
    const preferred = vietnameseNano || defaults.find(voiceReady) || defaults[0] || choices.find(voiceReady);
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
  if (voice?.engine !== appliedRenderEngine) applyRenderMode($('render-mode').value, {remember: false});
  const ready = voiceReady(voice);
  $('voice-status').className = `voice-status ${ready ? 'ready' : 'missing'}`;
  $('voice-status-title').textContent = !voice ? 'Chưa có giọng phù hợp' : ready ? `${engineName(voice)} · Sẵn sàng sử dụng` : `${engineName(voice)} · Cần tải mô hình`;
  $('voice-status-detail').textContent = !voice ? 'Chọn ngôn ngữ khác hoặc thêm mẫu giọng cá nhân được hỗ trợ.' : ready ? (voice.description || 'Giọng đã có trên máy.') : voiceSetupMessage(voice);
  $('generate').disabled = !ready || submitting;
  $('benchmark').disabled = !ready || submitting || !benchmarkSupported(voice);
  $('calibrate-machine').disabled = !ready || submitting || $('language').value !== 'vi' || !calibrationVoice(voice);
  $('calibrate-machine').title = calibrationVoice(voice) ? `Đo cấu hình nhiều tác vụ cho giọng ${voice.name} · ${engineName(voice)}.` : 'Tự tối ưu nhiều cấu hình hiện dùng Nano hoặc Turbo tiếng Việt. Với giọng đa ngôn ngữ, dùng Đo giọng đang chọn.';
  $('benchmark').title = benchmarkSupported(voice) ? 'Đo bằng giọng, ngôn ngữ và chế độ ưu tiên đang chọn.' : 'Chưa có lời đọc mẫu cho ngôn ngữ này.';
  $('nano-parallel').disabled = !cpuVoice(voice) || submitting;
  for (const option of $('nano-parallel').options) {
    const outsideBudget = voice?.engine === 'voxcpm' && Number(option.value) > 8;
    option.disabled = outsideBudget; option.hidden = outsideBudget;
  }
  $('nano-threads').disabled = !cpuVoice(voice) || submitting;
  $('nano-steps').disabled = voice?.engine !== 'vieneu_nano' || submitting;
  $('voxcpm-steps').disabled = voice?.engine !== 'voxcpm' || submitting;
  $('international-precision').disabled = voice?.engine !== 'voxcpm' || submitting;
  $('nano-step-field').hidden = voice?.engine !== 'vieneu_nano';
  $('voxcpm-step-field').hidden = voice?.engine !== 'voxcpm';
  $('resource-note').textContent = cpuVoice(voice)
    ? voice.engine === 'voxcpm'
      ? 'Các tác vụ và luồng CPU áp dụng cho giọng đa ngôn ngữ đang chọn. Mỗi tác vụ dùng nhiều RAM; đo mẫu để kiểm tra tốc độ và chọn ít tác vụ hơn nếu máy thiếu RAM.'
      : `Các tác vụ CPU áp dụng cho giọng ${engineName(voice)} đang chọn. Nhiều tác vụ dùng thêm RAM; bấm tự đo để tìm cấu hình phù hợp. Số bước Nano được chỉnh riêng bên dưới.`
    : 'Giọng hiện tại dùng cơ chế xử lý riêng của mô hình.';
  updateSuggestion();
  updateRenderNote();
  $('generate-note').textContent = !voice ? 'Cần chọn giọng hỗ trợ ngôn ngữ lời đọc.' : !ready ? (voice.has_sample || voice.category === 'reference' ? 'Cài mô hình trước khi tạo giọng. Bạn vẫn có thể nghe mẫu trong Thư viện giọng.' : 'Tải mô hình trước khi tạo giọng. Mở Hướng dẫn để xem chi tiết.') : 'Tạo trên máy · Có thể dừng và tiếp tục trong Bản thu';
}

function updateCharacterCount() {
  const count = $('script').value.length;
  $('char-count').textContent = `${count.toLocaleString('vi-VN')} / 1.000.000`;
  $('char-count').classList.toggle('limit', count >= 1000000);
}

function scheduleCharacterCount() {
  if (characterCountFrame) return;
  characterCountFrame = requestAnimationFrame(() => {
    characterCountFrame = null;
    updateCharacterCount();
  });
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
  const signature = JSON.stringify([job.id, job.status, job.progress, job.phase, job.error, job.audio_seconds, job.duration_limited, job.speed_report, job.auto_fitted_cues, job.fit_warning_count, job.benchmark_note, job.calibration_report, job.execution_settings]);
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
  $('output-detail').textContent = `${job.voice_name || 'Giọng đọc'} · ${formatExecutionSettings(job)} · ${languageName(job.language)} · ${duration(job.audio_seconds)}${job.phase ? ` · ${job.phase}` : ''}`;
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
  if (done && job.engine === 'vieneu' && report && Number(report.spoken_realtime_multiplier ?? report.realtime_multiplier) < 30 && fastNanoVoice()) {
    $('output-actions').append(makeButton('Chuyển sang Nano và đo', chooseNanoAndBenchmark));
  }
  $('speed-report').hidden = !done || !report;
  $('speed-report').textContent = report ? formatSpeedReport(report) : '';
  speedSummary = done ? {version: config?.version, voice: job.voice_name, engine:job.engine, execution_settings:job.execution_settings, render_mode: job.render_mode, speed_report:report, calibration_report:job.calibration_report} : null;
  $('copy-speed-report').hidden = !done || (!report && !job.calibration_report);
  if (done && job.calibration_report) {
    const selected=job.calibration_report.selected;
    $('speed-report').hidden=false;
    $('speed-report').textContent=`Đã lưu cấu hình ${engineName({engine:job.calibration_report.engine || job.engine})} đo được: ${selected.settings.nano_parallel} tác vụ × ${selected.settings.nano_threads} luồng. Kết quả khi model đã nạp: ${formatSpeedReport(selected.warm)} Tổng thời gian thử các cấu hình: ${duration(job.calibration_report.total_calibration_seconds)}.`;
    if (appliedCalibrationId !== job.id) {
      appliedCalibrationId=job.id;
      api('/api/config').then(fresh => {
        config=fresh;
        const measuredProfile=job.resource_profile || job.calibration_report.resource_profile || 'maximum';
        if ($('voice').value===job.voice_id && $('render-mode').value===job.render_mode && $('resource-profile').value===measuredProfile) applyRenderMode(job.render_mode, {useSaved: false});
      }).catch(error => notify(error.message,true));
    }
  }
}

function formatExecutionSettings(job) {
  const actual=job.execution_settings;
  const engine=actual?.engine || job.engine;
  const parts=[engineName({engine})];
  if (actual) {
    if (cpuVoice({engine}) && Number(actual.workers)>0 && Number(actual.threads)>0) parts.push(`${actual.workers} tác vụ × ${actual.threads} luồng CPU`);
    if (actual.precision) parts.push(String(actual.precision).toUpperCase());
    if (engine==='vieneu_nano' && actual.nano_steps) parts.push(`${actual.nano_steps} bước`);
    if (engine==='voxcpm' && (actual.voxcpm_steps || actual.inference_steps)) parts.push(`${actual.voxcpm_steps || actual.inference_steps} bước`);
  } else if (activeStatuses.has(job.status) && cpuVoice({engine})) {
    parts.push(`yêu cầu ${job.nano_parallel || 1} tác vụ × ${job.nano_threads || 2} luồng CPU`);
  }
  return parts.join(' · ');
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
      resource_profile: $('resource-profile').value,
      nano_steps: Number($('nano-steps').value), nano_threads: Number($('nano-threads').value), nano_parallel: Number($('nano-parallel').value),
      ...(voice.engine === 'voxcpm' ? {voxcpm_steps: Number($('voxcpm-steps').value), international_precision: $('international-precision').value} : {})
    });
    setOutput(job); notify('Đã nhận nội dung. Bạn có thể theo dõi bản thu ở bên dưới.');
    await refreshHistory();
  } catch (error) { notify(error.message, true); }
  finally { submitting = false; updateVoice(); }
}

async function benchmark() {
  if (submitting) return;
  const voice = voices.find((item) => item.id === $('voice').value);
  if (!benchmarkSupported(voice)) { notify('Chưa có lời đọc mẫu cho ngôn ngữ đang chọn.', true); return; }
  if (!voiceReady(voice)) { notify('Chọn giọng đã sẵn sàng trước khi đo tốc độ.', true); return; }
  submitting = true; updateVoice(); notify('');
  try {
    const job = await post('/api/benchmark', {
      voice_id: voice.id, language: $('language').value,
      render_mode: $('render-mode').value, delivery: $('delivery').value,
      resource_profile: $('resource-profile').value,
      nano_steps: Number($('nano-steps').value), nano_parallel: Number($('nano-parallel').value),
      nano_threads: Number($('nano-threads').value), audio_fit_backend: $('audio-fit-backend').value, quality: $('quality').value,
      ...(voice.engine === 'voxcpm' ? {voxcpm_steps: Number($('voxcpm-steps').value), international_precision: $('international-precision').value} : {})
    });
    setOutput(job);
    notify('Đang tạo mẫu ngắn để đo tốc độ. Kết quả và ước tính tạo 1 giờ lời đọc sẽ hiện ở Bản thu.');
    await refreshHistory();
    $('output-heading').scrollIntoView({block: 'center', behavior: 'auto'});
  } catch (error) { notify(error.message, true); }
  finally { submitting = false; updateVoice(); }
}

async function chooseNanoAndBenchmark() {
  if (submitting) return;
  const voice=fastNanoVoice();
  if (!voice) { notify('Chọn tiếng Việt và tải giọng Nano trước khi đo so sánh.', true); return; }
  $('voice').value=voice.id;
  applyRenderMode('fast', {useSaved: false});
  updateVoice();
  await benchmark();
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
    .filter((voice) => filter === 'all' || (filter === 'ready' && voiceReady(voice)) || (filter === 'reference' && voice.category === 'reference') || (filter === 'cloned' && voice.category === 'cloned') || (filter === 'system' && voice.engine === 'system'))
    .sort((a, b) => Number(b.category === 'reference' && b.is_default) - Number(a.category === 'reference' && a.is_default));
  const library = $('voice-library'); library.replaceChildren();
  if (!entries.length) { library.append(node('div', 'Chưa có giọng phù hợp. Thử đổi bộ lọc hoặc thêm mẫu giọng bên dưới.', 'empty-state')); return; }
  for (const voice of entries) {
    const card = node('article', null, 'card voice-card');
    const heading = node('div', null, 'voice-card-heading');
    const icon = node('span', '≋', 'voice-icon'); icon.setAttribute('aria-hidden', 'true');
    const title = node('div'); title.append(node('h3', voice.name), node('p', engineName(voice)));
    heading.append(icon, title); card.append(heading, node('p', voice.description || 'Giọng đọc được cài trên máy.'));
    const tags = node('div', null, 'tags');
    tags.append(node('span', voice.category === 'reference' ? (voice.is_default ? 'MẶC ĐỊNH CỦA BẠN' : 'GIỌNG MẪU CỦA BẠN') : voice.category === 'cloned' ? 'GIỌNG CÁ NHÂN' : voice.engine === 'system' ? 'GIỌNG HỆ THỐNG' : 'GIỌNG CÓ SẴN', 'small-tag'));
    if (voice.native_language) tags.append(node('span', `Bản ngữ · ${languageName(voice.native_language)}`, 'small-tag'));
    for (const language of (voice.languages || []).slice(0, 2)) tags.append(node('span', languageName(language), 'small-tag'));
    if ((voice.languages || []).length > 2) tags.append(node('span', `+${voice.languages.length - 2} ngôn ngữ`, 'small-tag'));
    card.append(tags);
    const ready = voiceReady(voice);
    card.append(node('p', ready ? '● Sẵn sàng sử dụng' : `○ ${voice.missing_reason || 'Chưa tải mô hình'} · ${modelInstruction(voice)}`, `readiness ${ready ? 'ready' : 'missing'}`));
    if (voice.has_sample || voice.category === 'reference' || voice.category === 'cloned') {
      const audio = node('audio'); audio.controls = true; audio.preload = 'none'; audio.src = voice.sample_url || `/api/voices/${encodeURIComponent(voice.id)}/sample`;
      audio.setAttribute('aria-label', `Nghe mẫu giọng ${voice.name}`); card.append(audio);
    }
    const controls = node('div', null, 'button-row');
    controls.append(makeButton('Chọn giọng →', async () => {
      const supported = (value) => [...$('language').options].some((option) => option.value === value);
      const language = voice.native_language && (voice.languages || []).includes(voice.native_language) && supported(voice.native_language)
        ? voice.native_language : (voice.languages || []).find(supported);
      if (!language) throw new Error('Chưa có ngôn ngữ phù hợp cho giọng này.');
      $('language').value = language; populateVoices(); $('voice').value = voice.id; updateVoice();
      saveRenderPreferences();
      showView('create'); $('script').focus();
      if (!ready) notify(voiceSetupMessage(voice), true);
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
  const excerpt = job.text_excerpt ?? job.text ?? '';
  card.append(heading, node('p', `${excerpt.slice(0, 220)}${(job.text_length ?? excerpt.length) > 220 ? '…' : ''}`, 'history-excerpt'));
  card.append(node('p', historyProgressText(job), 'field-note history-progress-note'));
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
  actions.append(makeButton('Mở bản thu ↗', async () => { setOutput(history.find((item) => item.id === job.id) || job); showView('create'); $('output-heading').scrollIntoView({block: 'center', behavior: 'auto'}); }));
  controls.append(actions);
  if (!activeStatuses.has(job.status)) controls.append(makeButton('Xóa', async () => {
    if (!window.confirm('Xóa bản thu và những tệp âm thanh của bản thu này khỏi máy?')) return;
    await api(`/api/history/${encodeURIComponent(job.id)}`, {method: 'DELETE'});
    if (selectedJob?.id === job.id) resetOutput();
    await refreshHistory(); notify('Đã xóa bản thu.');
  }, 'text-button danger-button'));
  card.append(controls); return card;
}

function historyProgressText(job) {
  return `${Number(job.progress) || 0}% · ${duration(job.audio_seconds)}${job.completed !== undefined && job.total ? ` · ${job.completed}/${job.total} đoạn xử lý` : ''}${job.phase ? ` · ${job.phase}` : ''}`;
}

function resetOutput() {
  selectedJob = null; outputSignature = '';
  $('output-heading').textContent = 'Âm thanh của bạn sẽ xuất hiện ở đây';
  $('output-detail').textContent = 'Tạo bản thu đầu tiên hoặc mở một bản thu trong lịch sử.';
  for (const id of ['output-status', 'output-progress', 'output-warning', 'output-audio', 'speed-report', 'benchmark-note', 'copy-speed-report']) $(id).hidden = true;
  $('output-audio').pause(); $('output-audio').removeAttribute('src'); $('output-audio').load();
  $('output-actions').replaceChildren();
}

function renderHistory() {
  $('history-count').textContent = String(history.length);
  // The create screen does not need a hidden collection of audio controls.
  if (currentView !== 'history') return;
  const list = $('history-list');
  const more = $('history-more');
  more.hidden = history.length <= historyVisibleCount;
  more.textContent = `Hiện thêm ${Math.min(20, Math.max(0, history.length - historyVisibleCount))} bản thu`;
  if (!history.length) {
    historyNodes.clear(); list.replaceChildren(); const empty = node('div', null, 'empty-state');
    empty.append(node('strong', 'Chưa có bản thu nào'), node('span', 'Tạo giọng từ lời đọc của bạn; âm thanh và các tác vụ sẽ được lưu tại đây.'));
    list.append(empty); return;
  }
  if (list.firstElementChild?.classList.contains('empty-state')) list.replaceChildren();
  const visible = history.slice(0, historyVisibleCount);
  // Keep a currently playing row if a new recording pushes it off this page.
  for (const [id, entry] of historyNodes) {
    const audio = entry.element.querySelector('audio');
    if (audio && !audio.paused && !visible.some((job) => job.id === id)) {
      const playing = history.find((job) => job.id === id);
      if (playing) visible.push(playing);
    }
  }
  const ids = new Set(visible.map((job) => job.id));
  for (const [id, entry] of historyNodes) if (!ids.has(id)) { entry.element.remove(); historyNodes.delete(id); }
  visible.forEach((job, index) => {
    const signature = JSON.stringify([job.status, job.progress, job.phase, job.completed, job.audio_seconds, job.error, job.duration_limited]);
    let entry = historyNodes.get(job.id);
    if (entry && entry.signature !== signature && entry.job.status === job.status && entry.job.error === job.error && entry.job.duration_limited === job.duration_limited) {
      // Preserve the card and media element while only progress is changing.
      entry.element.querySelector('.history-progress-note').textContent = historyProgressText(job);
      const progress = entry.element.querySelector('progress');
      if (progress) progress.value = Number(job.progress) || 0;
      entry.signature = signature;
    } else if (!entry || entry.signature !== signature) {
      const element = historyCard(job);
      if (entry) entry.element.replaceWith(element);
      entry = {element, signature, job}; historyNodes.set(job.id, entry);
    }
    entry.job = job;
    if (list.children[index] !== entry.element) list.insertBefore(entry.element, list.children[index] || null);
  });
}

async function refreshHistory() {
  const result = await api('/api/history?compact=true');
  history = (result.items || []).filter((job) => /^[a-f0-9]{32}$/.test(job.id));
  renderHistory();
  if (selectedJob) {
    const updated = history.find((job) => job.id === selectedJob.id);
    if (updated) setOutput(updated);
  }
  if (!polling && history.some((job) => activeStatuses.has(job.status))) schedulePoll(3000);
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
  const initial = !renderSettingsInitialized;
  populateResourceProfiles();
  if (initial) {
    $('resource-profile').value = resourceProfiles.has(renderPreferences.resource_profile) ? renderPreferences.resource_profile : 'smooth';
    $('international-precision').value = renderPreferences.international_precision === 'int8' ? 'int8' : 'fp32';
    updateResourceNote();
  }
  if (initial && renderModes.has(renderPreferences.mode)) $('render-mode').value = renderPreferences.mode;
  populateLanguages();
  if (initial && [...$('language').options].some((option) => option.value === renderPreferences.language)) $('language').value = renderPreferences.language;
  populateVoices();
  if (initial) {
    if ([...$('voice').options].some((option) => option.value === renderPreferences.voice_id)) {
      $('voice').value = renderPreferences.voice_id;
      updateVoice();
    }
    applyRenderMode($('render-mode').value, {remember: false});
    renderSettingsInitialized = true;
  }
  renderLibrary(); renderModelStatus();
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
    const active = history.some((job) => activeStatuses.has(job.status));
    schedulePoll(document.hidden ? (active ? 15000 : 60000) : (active ? 3000 : 15000));
  }
}

function schedulePoll(delay) {
  clearTimeout(pollTimer);
  pollTimer = setTimeout(poll, delay);
}

for (const button of document.querySelectorAll('[data-view]')) button.addEventListener('click', () => showView(button.dataset.view));
$('language').addEventListener('change', () => { populateVoices(); saveRenderPreferences(); });
$('voice').addEventListener('change', () => { updateVoice(); saveRenderPreferences(); });
$('script').addEventListener('input', scheduleCharacterCount);
$('script-format').addEventListener('change', updateFormat);
$('speed').addEventListener('input', () => { $('speed-value').textContent = `${Number($('speed').value).toLocaleString('vi-VN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}×`; });
$('delivery').addEventListener('change', updateDelivery);
$('paragraph-pause').addEventListener('input', () => { paragraphPauseEdited = true; });
$('render-mode').addEventListener('change', () => applyRenderMode($('render-mode').value));
$('resource-profile').addEventListener('change', () => {
  updateResourceNote();
  applyResourceBudget();
});
$('international-precision').addEventListener('change', applyResourceBudget);
$('optimize-speed').addEventListener('click', () => {
  applyRenderMode('fast', {useSaved: false});
  const voice=voices.find((item)=>item.id===$('voice').value);
  notify(`Đã giữ giọng ${voice?.name || 'đang chọn'} và áp dụng cấu hình ${engineName(voice)} ưu tiên tốc độ. Bấm Đo giọng đang chọn để kiểm tra trước khi tạo bản dài.`);
});
$('choose-nano').addEventListener('click', chooseNanoAndBenchmark);
$('nano-parallel').addEventListener('change', rememberRenderTuning);
$('nano-threads').addEventListener('input', rememberRenderTuning);
$('nano-steps').addEventListener('change', rememberRenderTuning);
$('voxcpm-steps').addEventListener('change', rememberRenderTuning);
$('audio-fit-backend').addEventListener('change', rememberRenderTuning);
$('quality').addEventListener('change', rememberRenderTuning);
$('suggest-voice').addEventListener('click', () => {
  const suggested = suggestedVoice();
  if (!suggested) { notify('Chưa có giọng gợi ý sẵn sàng. Chọn giọng khác hoặc tải thêm giọng trong Thư viện giọng.', true); return; }
  $('voice').value = suggested.id; updateVoice();
  saveRenderPreferences();
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
$('history-more').addEventListener('click', () => { historyVisibleCount += 20; renderHistory(); });
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
  schedulePoll(3000);
}
init();

$('cue-fit').addEventListener('change', updateFormat);


$('calibrate-machine').addEventListener('click', async () => {
  const voice=voices.find(item=>item.id===$('voice').value);
  if (submitting || !voiceReady(voice) || !calibrationVoice(voice) || $('language').value !== 'vi')return;
  submitting=true;updateVoice();
  try {
    const job=await post('/api/calibrate',{voice_id:voice.id,language:$('language').value,render_mode:$('render-mode').value,resource_profile:$('resource-profile').value,delivery:$('delivery').value});
    setOutput(job);await refreshHistory();
    notify('Đang thử nhiều cấu hình CPU bằng lời đọc thật. Có thể mất vài phút và dùng nhiều CPU/RAM; cấu hình tốt nhất sẽ được lưu. Có thể bấm Dừng tạo.');
    $('output-heading').scrollIntoView({block:'center',behavior:'auto'});
  } catch(error) {notify(error.message,true);}
  finally {submitting=false;updateVoice();}
});
$('copy-speed-report').addEventListener('click', async () => {
  try {await navigator.clipboard.writeText(JSON.stringify(speedSummary,null,2));notify('Đã sao chép kết quả đo. Bạn có thể dán vào cuộc trò chuyện.');}
  catch {notify('Chưa sao chép được. Hãy chọn và sao chép nội dung kết quả đo đang hiện.',true);}
});
