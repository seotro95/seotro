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
  const signature = JSON.stringify([job.id, job.status, job.progress, job.phase, job.error, job.audio_seconds, job.duration_limited, job.speed_report, job.auto_fitted_cues, job.fit_warning_count]);
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
  $('speed-report').textContent = report?.realtime_multiplier
    ? `Tốc độ đo trên bản thu này: ${report.realtime_multiplier}× thời gian thực · ${duration(report.measurement_audio_seconds)} âm thanh / ${Number(report.measurement_elapsed_seconds).toLocaleString('vi-VN')} giây xử lý. Kết quả thay đổi theo mô hình, cấu hình và nội dung.`
    : '';
}

async function generate() {
  if (submitting) return;
  if (!$('script').value.trim()) { notify('Hãy nhập nội dung cần đọc.', true); $('script').focus(); return; }
  if ($('script').value.length > 1000000) { notify('Mỗi lần tạo nhận tối đa 1.000.000 ký tự.', true); return; }
  for (const id of ['max-minutes', 'paragraph-pause']) if (!$(id).reportValidity()) return;
  const voice = voices.find((item) => item.id === $('voice').value);
  if (!voiceReady(voice)) { notify('Chọn một giọng đã sẵn sàng hoặc tải mô hình trước.', true); return; }
  submitting = true; updateVoice(); notify('');
  try {
    const job = await post('/api/speech', {
      text: $('script').value, voice_id: voice.id, language: $('language').value,
      input_format: $('script-format').value, skip_timestamps: $('skip-timestamps').checked,
      speed: Number($('speed').value), format: $('format').value,
      max_minutes: Number($('max-minutes').value), delivery: $('delivery').value,
      paragraph_pause: Number($('paragraph-pause').value), quality: $('quality').value,
      cue_fit: $('cue-fit').value, max_cue_tempo: Number($('cue-tempo').value),
      nano_steps: Number($('nano-steps').value), nano_threads: 2, nano_parallel: Number($('nano-parallel').value)
    });
    setOutput(job); notify('Đã nhận nội dung. Bạn có thể theo dõi bản thu ở bên dưới.');
    await refreshHistory();
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
$('script').addEventListener('input', updateCharacterCount);
$('script-format').addEventListener('change', updateFormat);
$('speed').addEventListener('input', () => { $('speed-value').textContent = `${Number($('speed').value).toLocaleString('vi-VN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}×`; });
$('delivery').addEventListener('change', () => { $('delivery-note').textContent = deliveryNotes[$('delivery').value]; });
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
