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
function engineName(voice) {
  return {vieneu_nano: 'Nano', vieneu: 'VieNeu', qwen: 'Qwen', qwen_clone: 'Qwen · Nhân bản', system: 'Hệ thống Windows'}[voice?.engine] || voice?.engine || 'AI';
}

function cloneEngine() {
  return $('language').value === 'vi' && voices.find((voice) => voice.id === $('voice').value)?.category === 'cloned'
    ? $('clone-engine').value : 'auto';
}

function selectedEngine(voice) {
  return voice?.category === 'cloned' && $('language').value === 'vi'
    ? cloneEngine() === 'nano' ? 'vieneu_nano' : 'vieneu' : voice?.engine;
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
  for (const voice of voices) if (voice.engine === 'system') for (const language of voice.languages || []) available.add(language);
  const options = Object.entries(config.languages || {}).filter(([key]) => available.has(key));
  $('language').replaceChildren(...options.map(([key, label]) => {
    const option = node('option', label); option.value = key; return option;
  }));
  if (available.has(previous)) $('language').value = previous;
  else if (available.has('vi')) $('language').value = 'vi';
  $('language').disabled = !options.length;
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
  const ready = selectedVoiceReady(voice);
  $('clone-engine-field').hidden = !(voice?.category === 'cloned' && $('language').value === 'vi');
  $('voice-status').className = `voice-status ${ready ? 'ready' : 'missing'}`;
  const engineLabel = voice?.category === 'cloned' && $('language').value === 'vi' ? `${selectedEngine(voice) === 'vieneu_nano' ? 'Nano' : 'VieNeu'} · Nhân bản` : engineName(voice);
  $('voice-status-title').textContent = !voice ? 'Chưa có giọng phù hợp' : ready ? `${engineLabel} · Sẵn sàng sử dụng` : `${engineLabel} · Cần tải mô hình`;
  const nanoAlternative = !ready && voice?.category === 'cloned' && $('language').value === 'vi' && cloneReadyEngines(voice).vieneu_nano && selectedEngine(voice) !== 'vieneu_nano';
  $('voice-status-detail').textContent = !voice ? 'Chọn ngôn ngữ khác hoặc thêm mẫu giọng cá nhân được hỗ trợ.' : ready ? (voice.description || 'Giọng đã có trên máy.') : nanoAlternative ? 'Nhân bản Nano đã sẵn sàng. Bấm Ưu tiên tốc độ hoặc chọn Nhân bản Nano để dùng nguyên mẫu giọng này.' : `Trong thư mục tool, chạy ${modelInstruction(voice, selectedEngine(voice))}, rồi bấm Kiểm tra lại ở Thư viện giọng.`;
  $('generate').disabled = !ready || submitting;
  $('generate-note').textContent = !voice ? 'Cần chọn giọng hỗ trợ ngôn ngữ lời đọc.' : !ready ? 'Tải mô hình trước khi tạo giọng. Mở Hướng dẫn để xem chi tiết.' : 'Tạo trên máy · Có thể dừng và tiếp tục trong Bản thu';
  updateAcceleration();
}

function accelerationSettings() {
  return {
    nano_parallel: $('nano-parallel').value === 'auto' ? 0 : Number($('nano-parallel').value),
    nano_threads: $('nano-threads').value === 'auto' ? 0 : Number($('nano-threads').value)
  };
}

function speedPresetVoice() {
  const current = voices.find((voice) => voice.id === $('voice').value);
  if ($('language').value !== 'vi' || !current || current.engine === 'system') return null;
  if (current.category === 'cloned') return current;
  return (current.engine === 'vieneu_nano' && voiceReady(current) ? current : null)
    || voices.find((voice) => voice.engine === 'vieneu_nano' && voice.category !== 'cloned' && voiceReady(voice) && (voice.languages || []).includes('vi'));
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
    : voice?.category === 'cloned' && $('language').value === 'vi' ? 'Ưu tiên tốc độ dùng nhân bản Nano và giữ mẫu giọng của bạn. Cần tải mô hình nhân bản Nano trước khi tạo.'
    : 'Ưu tiên tốc độ dùng Nano tiếng Việt. Giọng hệ thống và ngôn ngữ đang chọn được giữ nguyên.';
}

function applySpeedPreset() {
  const voice = speedPresetVoice();
  if (!voice) return;
  $('voice').value = voice.id;
  if (voice.category === 'cloned') $('clone-engine').value = 'nano';
  $('nano-steps').value = '4'; $('nano-parallel').value = 'auto'; $('nano-threads').value = 'auto';
  $('paragraph-pause').value = '0'; $('delivery').value = 'natural'; $('quality').value = 'auto';
  $('speed').value = '1'; $('format').value = 'wav';
  $('speed-value').textContent = '1,00×'; $('delivery-note').textContent = deliveryNotes.natural;
  updateVoice();
  const ready = selectedVoiceReady(voice);
  notify(`Đã ${voice.category === 'cloned' ? 'giữ mẫu giọng' : 'chọn giọng'} ${voice.name}, Nano 4 bước, đọc tự nhiên và WAV. ${ready ? 'Ít bước có thể giảm độ tự nhiên; bấm Đo tốc độ thực để kiểm tra máy của bạn.' : `Chạy ${modelInstruction(voice, selectedEngine(voice))} trong thư mục tool, rồi Kiểm tra lại ở Thư viện giọng.`}`, !ready);
}

function generationSettings(voice) {
  return {
    voice_id: voice.id, language: $('language').value, clone_engine: cloneEngine(),
    speed: Number($('speed').value), format: $('format').value,
    delivery: $('delivery').value, paragraph_pause: Number($('paragraph-pause').value),
    quality: $('quality').value, nano_steps: Number($('nano-steps').value),
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
  $('skip-timestamps').disabled = srt;
  $('format-note').textContent = srt ? 'SRT · Giữ mốc thời gian' : 'TXT · Văn bản thuần';
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
  const signature = JSON.stringify([job.id, job.status, job.progress, job.phase, job.error, job.audio_seconds, job.duration_limited, job.speed_report, job.benchmark]);
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
    const job = await post('/api/speech', {
      ...generationSettings(voice), text: $('script').value,
      input_format: $('script-format').value, skip_timestamps: $('skip-timestamps').checked,
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
  const text = (await file.text()).replace(/^\uFEFF/, '');
  if (text.length > 200000) throw new Error('Tệp vượt quá 200.000 ký tự. Hãy chia nội dung thành các phần trước khi nhập.');
  if (!text.trim()) throw new Error('Tệp chưa có nội dung để đọc.');
  if (text.includes('\uFFFD')) throw new Error('Tệp có ký tự không đọc được. Hãy lưu TXT/SRT bằng UTF-8 rồi nhập lại.');
  const format = /\.srt$/i.test(file.name) ? 'srt' : 'txt';
  if (format === 'srt') await post('/api/scripts/convert', {text, input_format: 'srt', output_format: 'srt'});
  if ($('script').value.trim() && !window.confirm('Thay nội dung đang nhập bằng nội dung trong tệp?')) return;
  $('script').value = text; $('script-format').value = format;
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
    .filter((voice) => filter === 'all' || (filter === 'ready' && libraryVoiceReady(voice)) || (filter === 'cloned' && voice.category === 'cloned') || (filter === 'system' && voice.engine === 'system'));
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
    const ready = libraryVoiceReady(voice);
    const readinessLabel = voice.category === 'cloned' ? `${ready ? '●' : '○'} ${cloneReadinessLabel(voice)}` : ready ? '● Sẵn sàng sử dụng' : `○ Chưa tải · ${modelInstruction(voice)}`;
    card.append(node('p', readinessLabel, `readiness ${ready ? 'ready' : 'missing'}`));
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
      if (!selectedVoiceReady(voice) && voice.category === 'cloned' && language === 'vi' && cloneReadyEngines(voice).vieneu_nano) {
        notify('Nhân bản Nano đã sẵn sàng cho mẫu giọng này. Bấm Ưu tiên tốc độ hoặc chọn Nhân bản Nano để sử dụng.');
      } else if (!selectedVoiceReady(voice)) {
        notify(`Giọng này cần mô hình đang chọn. Chạy ${modelInstruction(voice, selectedEngine(voice))} trong thư mục tool rồi kiểm tra lại.`, true);
      } else notify('');
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
  for (const id of ['output-status', 'output-progress', 'output-warning', 'output-audio', 'speed-report']) $(id).hidden = true;
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
  target.append(node('p', `${config.nano_clone_ready ? '●' : '○'} Nhân bản Nano: ${config.nano_clone_ready ? 'Đã tải' : 'Chưa tải · TAI_GIONG_NHAN_BAN_NHANH.bat'}`));
  if (config.acceleration) target.append(node('p', `Nano tự động: ${config.acceleration.recommended_workers || 1} đoạn cùng lúc · ${config.acceleration.recommended_threads || 2} luồng CPU mỗi đoạn.`));
  target.append(node('p', 'Giọng hệ thống Windows có thể dùng ngay khi đã được cài trong hệ điều hành.'));
}

async function refreshVoices() {
  const results = await Promise.all([api('/api/config'), api('/api/voices')]);
  config = results[0]; voices = results[1].voices || [];
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
$('clone-engine').addEventListener('change', updateVoice);
$('script').addEventListener('input', updateCharacterCount);
$('script-format').addEventListener('change', updateFormat);
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
    if (config.portable) {
      const steps = document.querySelector('.help-steps');
      steps.replaceChildren();
      for (const message of [
        'Giải nén toàn bộ ZIP, mở MO_TOOL.bat. Python, FFmpeg và các mô hình tiếng Việt đã có sẵn; không cần cài đặt hoặc tải thêm.',
        'Thêm hoặc chọn mẫu giọng cá nhân tiếng Việt, rồi bấm Ưu tiên tốc độ để dùng nhân bản Nano 4 bước. Nghe thử để kiểm tra độ giống giọng.',
        'Nhập tối đa 200.000 ký tự hoặc TXT/SRT, tạo giọng rồi tải WAV/MP3/TXT/SRT. Giữ cửa sổ tool mở khi sử dụng.',
        'Sao lưu app/.data trước khi cập nhật hoặc xóa tool. Gói Portable này chuẩn bị sẵn giọng Việt/Anh tiêu chuẩn và nhân bản tiếng Việt trên CPU.'
      ]) steps.append(node('li', message));
      for (const code of document.querySelectorAll('#help-dialog code')) {
        if ((code.textContent || '').startsWith('TAI_GIONG_')) code.parentElement.textContent = 'Mô hình nhân bản Nano đã có sẵn trong bản Portable. Chọn mẫu giọng tiếng Việt rồi bấm Ưu tiên tốc độ. Nano 4 bước có thể giảm độ tự nhiên; cần nghe thử.';
      }
    }
    if (history[0]) setOutput(history[0]);
    if (!voices.some(libraryVoiceReady)) notify('Phòng thu đã mở. Chưa có giọng sẵn sàng; xem Hướng dẫn để tải mô hình trước khi tạo âm thanh.');
  } catch (error) { notify(error.message, true); setConnection(false); connectionFailed = true; }
  pollTimer = setTimeout(poll, 3000);
}
init();
