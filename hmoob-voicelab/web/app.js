'use strict';

const $ = id => document.getElementById(id);
const number = new Intl.NumberFormat('vi-VN');
const activeStatuses = new Set(['queued', 'running', 'cancelling']);
const statusNames = {queued: 'Đang chờ', running: 'Đang tạo giọng', cancelling: 'Đang dừng', cancelled: 'Đã dừng', error: 'Cần kiểm tra', done: 'Hoàn tất'};
const qualityNames = {fast: 'Nhanh · 16 bước', standard: 'Chất lượng · 32 bước', draft: 'Bản nháp · 8 bước'};
const state = {maxCharacters: 1000000, characters: 0, status: null, voices: [], selectedJob: null, jobs: [], submitting: false, referenceDirty: false, countTimer: null, pollTimer: null, polling: false, view: 'create', previewEnd: null};
const partNodes = new Map();
const historyNodes = new Map();

function codepoints(value) {
  let count = 0;
  for (const unused of value) count++;
  return count;
}

function notice(message, error = false) {
  const node = $('notice');
  node.textContent = message;
  node.classList.toggle('error', error);
  node.hidden = !message;
}

async function api(path, options = {}) {
  const response = await fetch(path, {...options, headers: {'Content-Type': 'application/json', ...options.headers}, cache: 'no-store'});
  let payload;
  try { payload = await response.json(); } catch { throw new Error('Máy chủ chưa trả dữ liệu hợp lệ. Kiểm tra cửa sổ đang chạy tool.'); }
  if (!response.ok) {
    let message = payload.error || payload.detail || payload.message;
    if (typeof message !== 'string') message = 'Không thực hiện được yêu cầu. Kiểm tra lại dữ liệu và trạng thái mô hình.';
    throw new Error(message);
  }
  return payload;
}

function selectedVoice() {
  return document.querySelector('input[name="voice"]:checked').value;
}

function currentVoice() {
  return state.voices.find(voice => voice.id === selectedVoice());
}

function updateGenerate() {
  const ready = Boolean(state.status?.engine?.ready && currentVoice()?.reference_ready && !state.referenceDirty);
  $('generate').disabled = state.submitting || !state.characters || state.characters > state.maxCharacters || !ready;
  $('generate').title = !state.status?.engine?.ready ? 'Cài bộ tạo giọng theo hướng dẫn của tool.' : state.referenceDirty || !currentVoice()?.reference_ready ? 'Lưu lời khớp đoạn mẫu trước khi tạo giọng.' : '';
}

function updateCount() {
  clearTimeout(state.countTimer);
  state.characters = codepoints($('script').value);
  $('character-count').textContent = number.format(state.characters);
  const over = state.characters > state.maxCharacters;
  $('character-count').parentElement.parentElement.classList.toggle('over-limit', over);
  $('capacity-fill').classList.toggle('over-limit', over);
  $('capacity-fill').style.width = Math.min(100, state.characters / state.maxCharacters * 100) + '%';
  $('script').setAttribute('aria-invalid', String(over));
  updateGenerate();
}

function showView(view) {
  state.view = view;
  $('create-view').hidden = view !== 'create';
  $('history-view').hidden = view !== 'history';
  for (const name of ['create', 'history']) {
    const button = $('nav-' + name);
    button.classList.toggle('active', name === view);
    if (name === view) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  }
  if (view === 'history') refreshJobs().catch(error => notice(error.message, true));
}

function renderVoice() {
  const voice = currentVoice();
  if (!voice) return;
  const audio = $('reference-audio');
  audio.pause();
  state.previewEnd = null;
  audio.src = voice.sample_url;
  const reference = voice.reference || {};
  state.referenceDirty = false;
  $('reference-start').value = reference.start ?? 0;
  $('reference-end').value = reference.end ?? Math.min(8, voice.duration || 8);
  $('reference-text').value = reference.text || '';
  $('reference-start').max = voice.duration || 30;
  $('reference-end').max = voice.duration || 30;
  $('reference-badge').textContent = voice.reference_ready ? 'Đã lưu lời' : 'Cần nhập lời';
  $('reference-badge').classList.toggle('saved', Boolean(voice.reference_ready));
  $('reference-info').textContent = `Bản gốc: ${Number(voice.duration || 0).toLocaleString('vi-VN', {maximumFractionDigits: 2})} giây. Lời tham chiếu được lưu riêng cho từng giọng.`;
  if (!voice.reference_ready) $('reference-panel').open = true;
  updateGenerate();
}

function markReferenceDirty() {
  state.referenceDirty = true;
  $('reference-badge').textContent = 'Chưa lưu';
  $('reference-badge').classList.remove('saved');
  updateGenerate();
}

async function refreshStatus() {
  const button = $('refresh-status');
  button.disabled = true;
  try {
    const data = await api('/api/status');
    state.status = data;
    state.maxCharacters = data.max_characters || 1000000;
    const engine = data.engine || {};
    $('engine-light').classList.toggle('ready', Boolean(engine.ready));
    $('engine-title').textContent = engine.ready ? `Bộ tạo giọng đã có trên máy${engine.device ? ' · ' + String(engine.device).toUpperCase() : ''}` : 'Cần chuẩn bị bộ tạo giọng';
    $('engine-description').textContent = engine.reason || (engine.ready ? 'Chọn đoạn mẫu, nhập lời tham chiếu và thử một câu ngắn trước khi đọc tài liệu dài.' : 'Chạy bộ cài giọng theo hướng dẫn README, sau đó bấm Kiểm tra lại.');
    updateCount();
  } finally { button.disabled = false; }
}

function duration(seconds) {
  seconds = Math.max(0, Math.floor(Number(seconds) || 0));
  return `${Math.floor(seconds / 3600)}:${String(Math.floor(seconds / 60) % 60).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
}

function estimate(seconds) {
  if (!Number.isFinite(seconds) || seconds <= 0) return 'Đang đo';
  if (seconds < 60) return 'Khoảng ' + Math.max(1, Math.ceil(seconds)) + ' giây';
  if (seconds < 3600) return 'Khoảng ' + Math.ceil(seconds / 60) + ' phút';
  return 'Khoảng ' + (seconds / 3600).toLocaleString('vi-VN', {maximumFractionDigits: 1}) + ' giờ';
}

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function button(text, handler, className = 'button button-light') {
  const node = element('button', text, className);
  node.addEventListener('click', handler);
  return node;
}

function download(text, path, filename, className = 'button button-light') {
  const link = element('a', text, className);
  // All output URLs must remain same-origin server paths, including mocked data.
  if (typeof path !== 'string' || !path.startsWith('/') || path.startsWith('//')) return link;
  link.href = path;
  if (filename) link.download = filename;
  return link;
}

function metric(label, value) {
  const item = element('span', label + ' ');
  item.append(element('strong', value));
  return item;
}

function renderCurrent(job) {
  if (!job) return;
  const previousId = state.selectedJob?.id;
  state.selectedJob = job;
  $('current-job').hidden = false;
  const progress = Math.min(100, Math.max(0, Number(job.progress) || 0));
  $('current-title').textContent = {queued: 'Bản thu đang trong hàng đợi', running: 'Đang biến kịch bản thành lời kể', cancelling: 'Đang dừng và giữ tiến độ', cancelled: 'Đã dừng · Có thể tiếp tục', error: 'Chưa hoàn tất bản thu', done: 'Câu chuyện đã thành lời'}[job.status] || 'Bản thu của bạn';
  $('current-caption').textContent = `${job.voice === 'male' ? 'Giọng nam' : 'Giọng nữ'} · ${number.format(job.characters || 0)} ký tự · ${qualityNames[job.quality] || job.quality || ''}`;
  $('current-percent').textContent = Math.floor(progress) + '%';
  $('current-progress').value = progress;
  const metrics = [metric('Đoạn đã đọc', `${number.format(job.completed_segments || 0)}/${number.format(job.total_segments || 0)}`), metric('Âm thanh', duration(job.audio_seconds)), metric('Xử lý', duration(job.processing_seconds))];
  if (Number.isFinite(job.speed_factor) && job.speed_factor > 0) metrics.push(metric('Tốc độ thực đo', job.speed_factor.toLocaleString('vi-VN', {maximumFractionDigits: 1}) + '× thời gian thực'));
  if (job.status === 'running') metrics.push(metric('Còn lại ước tính', estimate(job.estimated_remaining_seconds)));
  $('current-metrics').replaceChildren(...metrics);
  $('current-error').textContent = job.error || '';
  $('current-error').hidden = !job.error;
  const signature = job.id + ':' + job.status;
  if ($('current-actions').dataset.signature !== signature) {
    const actions = [];
    if (activeStatuses.has(job.status)) {
      const cancel = button(job.status === 'cancelling' ? 'Đang dừng…' : '■ Dừng, giữ tiến độ', () => jobAction(job.id, 'cancel'));
      cancel.disabled = job.status === 'cancelling';
      actions.push(cancel);
    }
    if (['cancelled', 'error'].includes(job.status)) actions.push(button('↻ Tiếp tục từ đoạn đã lưu', () => jobAction(job.id, 'resume'), 'button button-dark'));
    actions.push(download('↓ Kịch bản TXT', `/api/jobs/${encodeURIComponent(job.id)}/text`, 'kich-ban.txt'));
    if (job.status === 'done') actions.push(download('↓ Tải toàn bộ ZIP', `/api/jobs/${encodeURIComponent(job.id)}/archive`, `hmoob-${job.id}.zip`, 'button button-dark'));
    $('current-actions').replaceChildren(...actions);
    $('current-actions').dataset.signature = signature;
  }
  if (previousId !== job.id) {
    for (const item of partNodes.values()) item.audio.pause();
    partNodes.clear();
    $('current-parts').replaceChildren();
  }
  const parts = job.parts || [];
  const present = new Set(parts.map(part => part.name));
  for (const [name, item] of partNodes) {
    if (!present.has(name)) { item.audio.pause(); item.row.remove(); partNodes.delete(name); }
  }
  parts.forEach((part, index) => {
    if (partNodes.has(part.name)) return;
    const row = element('div', undefined, 'part-item');
    const title = element('div');
    title.append(element('strong', 'Chương ' + number.format(index + 1)), element('small', duration(part.audio_seconds)));
    const audio = element('audio');
    audio.controls = true;
    audio.preload = 'none';
    audio.setAttribute('aria-label', 'Nghe chương ' + (index + 1));
    const path = part.url;
    if (typeof path === 'string' && path.startsWith('/') && !path.startsWith('//')) audio.src = path;
    row.append(title, audio, download('Tải WAV ↓', path, part.name));
    $('current-parts').append(row);
    partNodes.set(part.name, {row, audio});
  });
  $('parts-note').hidden = !parts.length;
}

function renderHistory() {
  $('history-count').textContent = number.format(state.jobs.length);
  $('empty-history').hidden = Boolean(state.jobs.length);
  const ids = new Set(state.jobs.map(job => job.id));
  for (const [id, item] of historyNodes) {
    if (!ids.has(id)) { item.card.remove(); historyNodes.delete(id); }
  }
  state.jobs.forEach((job, index) => {
    let item = historyNodes.get(job.id);
    if (!item) {
      const card = element('article', undefined, 'card history-card');
      const top = element('div', undefined, 'history-top');
      const title = element('h3');
      const status = element('span');
      top.append(title, status);
      const caption = element('p');
      const progress = element('progress');
      progress.max = 100;
      progress.setAttribute('aria-label', 'Tiến độ bản thu');
      const bottom = element('div', undefined, 'history-bottom');
      const details = element('span');
      const open = button('Xem bản thu →', async () => {
        try {
          const result = await api(`/api/jobs/${encodeURIComponent(job.id)}`);
          renderCurrent(result.job);
          showView('create');
          $('current-job').scrollIntoView({behavior: 'smooth', block: 'start'});
          schedulePoll(1000);
        } catch (error) { notice(error.message, true); }
      });
      bottom.append(details, open);
      card.append(top, caption, progress, bottom);
      item = {card, title, status, caption, progress, details};
      historyNodes.set(job.id, item);
    }
    item.title.textContent = `${job.voice === 'male' ? 'Giọng nam' : 'Giọng nữ'} · ${number.format(job.characters || 0)} ký tự`;
    item.status.textContent = statusNames[job.status] || job.status;
    item.status.className = 'status-pill ' + (['done', 'error'].includes(job.status) ? job.status : '');
    let created = '';
    const date = new Date(job.created_at);
    if (!Number.isNaN(date.getTime())) created = date.toLocaleString('vi-VN', {dateStyle: 'short', timeStyle: 'short'});
    item.caption.textContent = `${created}${created ? ' · ' : ''}${qualityNames[job.quality] || job.quality || ''} · Âm thanh ${duration(job.audio_seconds)}`;
    item.progress.value = Math.min(100, Math.max(0, Number(job.progress) || 0));
    item.details.textContent = `${number.format(job.completed_segments || 0)}/${number.format(job.total_segments || 0)} đoạn · ${Math.floor(Number(job.progress) || 0)}%`;
    if ($('history-list').children[index] !== item.card) $('history-list').insertBefore(item.card, $('history-list').children[index] || null);
  });
}

async function refreshJobs() {
  const result = await api('/api/jobs');
  state.jobs = result.jobs || [];
  renderHistory();
  return state.jobs;
}

function schedulePoll(delay = 1500) {
  clearTimeout(state.pollTimer);
  state.pollTimer = setTimeout(poll, delay);
}

async function poll() {
  if (state.polling) return;
  state.polling = true;
  let retry = 1500;
  try {
    await refreshJobs();
    if (state.selectedJob) {
      const requestedId = state.selectedJob.id;
      const result = await api(`/api/jobs/${encodeURIComponent(requestedId)}`);
      if (state.selectedJob?.id === requestedId) renderCurrent(result.job);
    }
    retry = state.jobs.some(job => activeStatuses.has(job.status)) ? 1500 : 12000;
  } catch (error) {
    $('engine-description').textContent = 'Mất kết nối theo dõi tác vụ. Tool sẽ thử lại; tiến độ đã lưu trên máy vẫn được giữ.';
    retry = 5000;
  } finally { state.polling = false; schedulePoll(retry); }
}

async function jobAction(id, action) {
  try {
    const result = await api(`/api/jobs/${encodeURIComponent(id)}/${action}`, {method: 'POST', body: '{}'});
    renderCurrent(result.job);
    await refreshJobs();
    schedulePoll(500);
    notice(action === 'cancel' ? 'Đang dừng. Tool giữ các đoạn đã hoàn tất để tiếp tục.' : 'Đã yêu cầu tiếp tục từ tiến độ đã lưu.');
  } catch (error) { notice(error.message, true); }
}

$('script').addEventListener('input', () => {
  clearTimeout(state.countTimer);
  state.countTimer = setTimeout(updateCount, 180);
});

$('text-file').addEventListener('change', async event => {
  const file = event.target.files[0];
  if (!file) return;
  try {
    if (file.size > 4000000) throw new Error('Tệp TXT tối đa 4 MB. Tool nhận tối đa 1.000.000 ký tự.');
    let text;
    try { text = new TextDecoder('utf-8', {fatal: true}).decode(await file.arrayBuffer()).replace(/^\uFEFF/, ''); }
    catch { throw new Error('Không đọc được tệp UTF-8. Hãy lưu lại tệp TXT với mã hóa UTF-8.'); }
    if (codepoints(text) > state.maxCharacters) throw new Error('Nội dung vượt 1.000.000 ký tự. Chia thành nhiều tài liệu để giữ đủ lời.');
    if ($('script').value && !window.confirm('Thay kịch bản hiện tại bằng nội dung tệp TXT?')) return;
    $('script').value = text;
    updateCount();
    notice(`Đã nhập ${file.name} · ${number.format(state.characters)} ký tự.`);
  } catch (error) { notice(error.message, true); }
  finally { event.target.value = ''; }
});

$('clear-text').addEventListener('click', () => {
  if (!$('script').value || window.confirm('Xóa văn bản đang soạn? Các tác vụ đã tạo vẫn được giữ.')) {
    $('script').value = '';
    updateCount();
  }
});

$('example').addEventListener('click', () => {
  if ($('script').value && !window.confirm('Thay kịch bản hiện tại bằng câu mẫu Hmong?')) return;
  $('script').value = 'Nyob zoo, hnub no koj nyob li cas?';
  updateCount();
  $('script').focus();
});

document.querySelectorAll('input[name="voice"]').forEach(input => input.addEventListener('change', renderVoice));
['reference-start', 'reference-end', 'reference-text'].forEach(id => $(id).addEventListener('input', markReferenceDirty));

$('preview-reference').addEventListener('click', async () => {
  const start = Number($('reference-start').value);
  const end = Number($('reference-end').value);
  const voice = currentVoice();
  if (!Number.isFinite(start) || !Number.isFinite(end) || start < 0 || end - start < 3 || end - start > 8 || end > (voice?.duration || 0) + 0.001) {
    notice('Chọn một đoạn mẫu dài 3–8 giây nằm trong bản gốc.', true);
    return;
  }
  const audio = $('reference-audio');
  try {
    state.previewEnd = end;
    audio.currentTime = start;
    await audio.play();
  } catch { notice('Trình duyệt chưa phát được mẫu. Kiểm tra tệp âm thanh và thử lại.', true); }
});
$('reference-audio').addEventListener('timeupdate', () => {
  const audio = $('reference-audio');
  if (state.previewEnd !== null && audio.currentTime >= state.previewEnd) { audio.pause(); state.previewEnd = null; }
});
$('reference-audio').addEventListener('seeking', () => {
  if (state.previewEnd !== null && $('reference-audio').currentTime > state.previewEnd) state.previewEnd = null;
});

$('save-reference').addEventListener('click', async () => {
  const button = $('save-reference');
  const voice = currentVoice();
  const reference = {start: Number($('reference-start').value), end: Number($('reference-end').value), text: $('reference-text').value.trim()};
  try {
    if (!voice) throw new Error('Chưa tải được danh sách giọng mẫu. Thử tải lại trang.');
    if (!reference.text) throw new Error('Nhập chính xác lời Hmong của đoạn mẫu trước khi lưu.');
    if (!Number.isFinite(reference.start) || !Number.isFinite(reference.end) || reference.start < 0 || reference.end - reference.start < 3 || reference.end - reference.start > 8 || reference.end > voice.duration + 0.001) throw new Error('Đoạn mẫu cần dài 3–8 giây và nằm trong bản gốc.');
    button.disabled = true;
    const result = await api(`/api/voices/${encodeURIComponent(voice.id)}/reference`, {method: 'POST', body: JSON.stringify(reference)});
    if (result.voice) state.voices = state.voices.map(item => item.id === voice.id ? result.voice : item);
    else { const result = await api('/api/voices'); state.voices = result.voices || []; }
    renderVoice();
    notice('Đã lưu đoạn mẫu và lời tham chiếu cho ' + (voice.name || 'giọng đã chọn') + '. Hãy tạo một câu ngắn và nghe kiểm tra trước.');
  } catch (error) { notice(error.message, true); }
  finally { button.disabled = false; }
});

$('speed').addEventListener('input', () => { $('speed-value').textContent = Number($('speed').value).toLocaleString('vi-VN', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + '×'; });
$('quality').addEventListener('change', () => {
  $('quality-note').textContent = {fast: 'Ít bước suy luận hơn để giảm thời gian xử lý. Nghe thử trước khi tạo bản dài.', standard: 'Nhiều bước suy luận hơn, xử lý lâu hơn. Chất lượng còn phụ thuộc mô hình và mẫu tham chiếu.', draft: '8 bước là chế độ thử nghiệm, có thể giảm độ rõ hoặc phát âm sai. Chỉ dùng để nghe thử.'}[$('quality').value];
});

$('generate').addEventListener('click', async () => {
  if (state.submitting) return;
  updateCount();
  if (!state.characters || !$('script').value.trim()) { notice('Nhập kịch bản trước khi tạo giọng.', true); return; }
  if (state.characters > state.maxCharacters) { notice('Kịch bản vượt 1.000.000 ký tự. Tool giữ nguyên văn bản để bạn chia nhỏ.', true); return; }
  state.submitting = true;
  updateGenerate();
  try {
    const result = await api('/api/jobs', {method: 'POST', body: JSON.stringify({text: $('script').value, voice: selectedVoice(), quality: $('quality').value, speed: Number($('speed').value)})});
    notice('Đã lưu kịch bản và tạo tác vụ. Bạn có thể theo dõi tiến độ bên dưới.');
    renderCurrent(result.job);
    await refreshJobs();
    $('current-job').scrollIntoView({behavior: 'smooth', block: 'start'});
    schedulePoll(500);
  } catch (error) { notice(error.message, true); }
  finally { state.submitting = false; updateGenerate(); }
});

$('nav-create').addEventListener('click', () => showView('create'));
$('nav-history').addEventListener('click', () => showView('history'));
$('back-to-create').addEventListener('click', () => showView('create'));
$('refresh-history').addEventListener('click', () => refreshJobs().catch(error => notice(error.message, true)));
$('refresh-status').addEventListener('click', () => refreshStatus().catch(error => notice(error.message, true)));
document.addEventListener('visibilitychange', () => { if (!document.hidden) schedulePoll(200); });

async function initialize() {
  updateCount();
  const results = await Promise.allSettled([refreshStatus(), api('/api/voices'), refreshJobs()]);
  if (results[1].status === 'fulfilled') {
    state.voices = results[1].value.voices || [];
    renderVoice();
  }
  for (const result of results) if (result.status === 'rejected') notice(result.reason.message, true);
  const latest = state.jobs.find(job => activeStatuses.has(job.status)) || state.jobs[0];
  if (latest) {
    try { const result = await api(`/api/jobs/${encodeURIComponent(latest.id)}`); renderCurrent(result.job); }
    catch (error) { notice(error.message, true); }
  }
  updateGenerate();
  schedulePoll();
}

initialize();
