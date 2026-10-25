'use strict';
const $ = id => document.getElementById(id);
const MAX_CHARACTERS = 1000000;
const drafts = new Map(), jobs = new Map(), partNodes = new Map();
const activeStates = new Set(['running', 'queued', 'cancelling']);
const resumableStates = new Set(['failed', 'cancelled']);
let voices = [], status = null, displayedVoice = null, activeJob = null, selectedJob = null;
let submitting = false, saving = false, stopping = false, previewEnd = null;
let textCount = 0, hasText = false, countPending = false, countTimer = null, pollTimer = null, polling = false;
const selected = () => document.querySelector('input[name="voice"]:checked').value;
const current = () => voices.find(v => v.id === selected());
const readDraft = () => ({start: Number($('reference-start').value), end: Number($('reference-end').value), text: $('reference-text').value});
const equal = (a, b) => a && b && a.start === b.start && a.end === b.end && a.text.trim() === b.text.trim();
const message = (text, error = false) => { $('notice').textContent = text; $('notice').classList.toggle('error', error); };
const isBusy = () => submitting || Boolean(activeJob);
const engineReady = () => Boolean(status?.ready ?? status?.engine?.ready);
const formatNumber = value => Number(value).toLocaleString('vi-VN', {maximumFractionDigits: 2});

async function api(url, options = {}) {
  const r = await fetch(url, {...options, headers: {'Content-Type': 'application/json', ...options.headers}, cache: 'no-store'});
  let data;
  try { data = await r.json(); } catch { throw Error('Không đọc được phản hồi. Giữ cửa sổ MO_HMONG_NHANH.bat mở và thử lại.'); }
  if (!r.ok) throw Error(typeof data.detail === 'string' ? data.detail : typeof data.message === 'string' ? data.message : 'Dữ liệu chưa hợp lệ. Kiểm tra văn bản và đoạn mẫu.');
  return data;
}
function countCodepoints(text) {
  let count = 0;
  for (let index = 0; index < text.length; index++, count++) {
    const first = text.charCodeAt(index);
    if (first >= 0xD800 && first <= 0xDBFF && index + 1 < text.length) {
      const second = text.charCodeAt(index + 1);
      if (second >= 0xDC00 && second <= 0xDFFF) index++;
    }
  }
  return count;
}
function fitLongText() {
  // Avoid native wrapping of million-character paragraphs freezing the editor.
  const long = $('text').value.length > 100000;
  $('text').wrap = long ? 'off' : 'soft';
  $('long-text-note').hidden = !long;
}
function recount() {
  clearTimeout(countTimer);
  fitLongText();
  const text = $('text').value;
  textCount = countCodepoints(text); hasText = Boolean(text.trim()); countPending = false;
  $('count').textContent = textCount.toLocaleString('vi-VN');
  $('count-line').classList.toggle('error', textCount > MAX_CHARACTERS);
  $('text').setAttribute('aria-invalid', String(textCount > MAX_CHARACTERS));
  update();
}
function generationBlocker(requireText = true) {
  const voice = current();
  if (!engineReady()) return status?.engine?.reason || 'Chưa có bộ tạo giọng. Bấm Kiểm tra lại sau khi cài mô hình.';
  if (!voice) return 'Chưa tải được mẫu giọng.';
  if (!equal(readDraft(), voice.reference_settings)) return 'Lưu đoạn và lời mẫu đang sửa trước khi tạo giọng.';
  if (!voice.generation_configured) return voice.reason || 'Chuẩn bị đoạn mẫu và lời tham chiếu cho giọng đã chọn.';
  if (requireText && (countPending || !hasText)) return 'Nhập văn bản cần đọc.';
  if (requireText && textCount > MAX_CHARACTERS) return 'Văn bản vượt 1.000.000 ký tự. Nội dung được giữ nguyên để bạn chia nhỏ.';
  return '';
}
function update() {
  const voice = current(), busy = isBusy();
  const dirty = voice && !equal(readDraft(), voice.reference_settings), blocker = generationBlocker();
  $('generate').disabled = busy || saving || Boolean(blocker);
  $('generate').title = blocker;
  $('generate').textContent = busy ? 'Đang tạo giọng…' : 'Tạo giọng nói';
  $('benchmark').disabled = busy || saving || Boolean(generationBlocker(false));
  $('benchmark').title = generationBlocker(false);
  $('stop').disabled = !activeJob || stopping;
  $('stop').textContent = stopping ? 'Đang dừng…' : 'Dừng, giữ tiến độ';
  $('voice-state').textContent = dirty ? 'Đoạn mẫu có thay đổi chưa lưu.' : voice?.generation_configured ? `Giọng ${voice.name} đã có mẫu và sẵn sàng tạo lời đọc.` : voice?.reason || 'Đang tải mẫu giọng…';
  $('reference-state').textContent = dirty ? 'Chưa lưu thay đổi.' : voice?.reference_ready ? 'Đã lưu riêng cho giọng này.' : 'Chưa có lời tham chiếu.';
  for (const node of document.querySelectorAll('input[name="voice"],#text,#text-file,#speed,#quality,#style,#reference-start,#reference-end,#reference-text')) node.disabled = busy;
  $('save-reference').disabled = saving || busy || !voice;
  const job = jobs.get(selectedJob);
  $('resume').hidden = !job || !resumableStates.has(job.status);
  $('resume').disabled = busy || !engineReady();
}
function renderVoice() {
  if (displayedVoice) drafts.set(displayedVoice, readDraft());
  const voice = current();
  if (!voice) { update(); return; }
  displayedVoice = voice.id;
  const ref = drafts.get(voice.id) || voice.reference_settings;
  $('reference-player').pause(); previewEnd = null;
  $('reference-player').src = voice.reference;
  $('reference-start').value = ref.start; $('reference-end').value = ref.end;
  $('reference-start').max = $('reference-end').max = voice.reference_settings.duration;
  $('reference-text').value = ref.text;
  $('reference-name').textContent = voice.name;
  $('save-reference').textContent = 'Lưu mẫu cho giọng ' + voice.name;
  if (!voice.reference_ready) $('reference-panel').open = true;
  update();
}
function renderEngine() {
  const ready = engineReady(), hardware = status?.hardware || {}, engine = status?.engine || {};
  $('engine-state').classList.toggle('ready', ready);
  $('engine-state').textContent = ready ? 'Bộ tạo giọng đã có trên máy. Chuẩn bị mẫu một lần cho từng giọng, sau đó nhập văn bản để đọc.' : engine.reason || 'Chưa sẵn sàng tạo giọng.';
  const device = hardware.device || engine.device;
  $('device').textContent = hardware.probing ? 'Đang kiểm tra thiết bị… Bấm Kiểm tra lại để xem kết quả.' : device ? `Thiết bị: ${String(device).toUpperCase()}${hardware.device_name ? ' · ' + hardware.device_name : ''}${hardware.cpu_threads ? ' · ' + hardware.cpu_threads + ' luồng CPU' : ''}${hardware.reason ? '. ' + hardware.reason : ''}` : 'Thiết bị sẽ được xác định khi tạo giọng.';
}
async function refresh() {
  $('refresh').disabled = true;
  try {
    const [state, list] = await Promise.all([api('/api/status'), api('/api/voices')]);
    status = state; voices = list.voices; renderEngine(); renderVoice();
  } catch (e) { status = null; update(); message(e.message, true); }
  finally { $('refresh').disabled = false; }
}
function duration(value) {
  const seconds = Math.max(0, Math.floor(Number(value) || 0));
  return `${Math.floor(seconds / 3600)}:${String(Math.floor(seconds / 60) % 60).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
}
function estimate(value) {
  if (!Number.isFinite(value) || value <= 0) return 'Chưa đủ dữ liệu';
  if (value < 60) return `Khoảng ${Math.ceil(value)} giây`;
  if (value < 3600) return `Khoảng ${formatNumber(value / 60)} phút`;
  return `Khoảng ${formatNumber(value / 3600)} giờ`;
}
const statusLabels = {queued: 'Đang chờ', running: 'Đang tạo giọng', cancelling: 'Đang dừng', completed: 'Hoàn tất', failed: 'Có lỗi', cancelled: 'Đã dừng'};
function voiceName(job) { return voices.find(voice => voice.id === job.voice)?.name || (String(job.voice).endsWith('male') && !String(job.voice).endsWith('female') ? 'Nam' : 'Nữ'); }
function rememberJob(job) {
  if (!job || typeof job.id !== 'string') return;
  jobs.set(job.id, job);
  if (activeStates.has(job.status)) activeJob = job.id;
  else if (activeJob === job.id) { activeJob = null; stopping = false; }
}
function renderJobMenu() {
  const menu = $('job-select'), existing = new Map([...menu.options].map(option => [option.value, option]));
  const ordered = [...jobs.values()].sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || '')));
  for (const job of ordered) {
    const option = existing.get(job.id) || new Option('', job.id);
    option.textContent = `${job.benchmark ? 'Đo tốc độ' : 'Bản đọc'} · ${voiceName(job)} · ${statusLabels[job.status] || job.status}${job.characters ? ' · ' + formatNumber(job.characters) + ' ký tự' : ''}`;
    if (!existing.has(job.id)) menu.append(option);
  }
  if (selectedJob) menu.value = selectedJob;
  $('recordings').hidden = !jobs.size;
}
function renderParts(job) {
  const signature = job.id;
  if ($('parts').dataset.job !== signature) {
    for (const part of partNodes.values()) part.audio.pause();
    partNodes.clear(); $('parts').replaceChildren(); $('parts').dataset.job = signature;
  }
  for (const part of job.parts || []) {
    const number = Number(part.number);
    if (!Number.isInteger(number) || number < 1) continue;
    const url = `/api/speech/jobs/${encodeURIComponent(job.id)}/parts/${number}`;
    let item = partNodes.get(number);
    if (!item) {
      const row = document.createElement('div'); row.className = 'part';
      const heading = document.createElement('strong');
      const meta = document.createElement('span'); meta.className = 'hint';
      const audio = document.createElement('audio'); audio.controls = true; audio.preload = 'none'; audio.src = url;
      audio.setAttribute('aria-label', `Nghe chương ${number}`);
      const link = document.createElement('a'); link.className = 'file-button small'; link.href = url; link.textContent = 'Tải WAV ↓'; link.download = part.filename || `chuong-${number}.wav`;
      row.append(heading, meta, audio, link); $('parts').append(row);
      item = {row, heading, meta, audio}; partNodes.set(number, item);
    }
    item.heading.textContent = `Chương ${number}`; item.meta.textContent = duration(part.seconds);
  }
  $('parts-note').textContent = (job.parts || []).length ? 'Nghe hoặc tải từng chương. Các chương đã tạo được giữ lại khi dừng; bản dài tiếp tục thành chương mới.' : 'Chương âm thanh sẽ xuất hiện sau khi tạo đủ một phần. Tiến độ từng đoạn vẫn được lưu.';
}
function renderJob(job) {
  if (!job) return;
  $('recordings').hidden = false;
  const progress = Math.max(0, Math.min(100, Number(job.progress) || (job.status === 'completed' ? 100 : 0)));
  $('job-state').textContent = statusLabels[job.status] || job.status;
  $('job-voice').textContent = `Giọng ${voiceName(job)}${job.device ? ' · ' + String(job.device).toUpperCase() : ''}`;
  $('progress').value = progress; $('progress-value').textContent = `${Math.floor(progress)}%`;
  $('segments').textContent = `${formatNumber(job.completed || 0)} / ${formatNumber(job.total || 0)} đoạn`;
  $('audio-duration').textContent = duration(job.audio_seconds);
  $('elapsed').textContent = duration(job.elapsed_seconds);
  $('throughput').textContent = Number.isFinite(job.throughput) && job.throughput > 0 ? `${formatNumber(job.throughput)}× thời gian thực` : 'Đang đo';
  $('hour-estimate').textContent = estimate(job.estimated_seconds_for_hour);
  $('job-error').textContent = job.status === 'failed' ? job.message || 'Tác vụ gặp lỗi. Các đoạn đã hoàn tất được giữ lại.' : job.status === 'cancelled' ? 'Đã giữ tiến độ. Bấm Tiếp tục để đọc phần còn lại.' : '';
  $('job-error').hidden = !$('job-error').textContent;
  renderParts(job); renderJobMenu(); update();
}
async function refreshJobs() {
  const data = await api('/api/speech/jobs');
  for (const job of data.jobs || []) rememberJob(job);
  if (!selectedJob || !jobs.has(selectedJob)) selectedJob = activeJob || data.jobs?.[0]?.id || null;
  renderJobMenu(); if (selectedJob) renderJob(jobs.get(selectedJob));
  if (activeJob) schedulePoll();
  update();
}
function schedulePoll(delay = 1000) { clearTimeout(pollTimer); pollTimer = setTimeout(poll, delay); }
async function poll() {
  if (polling || !activeJob) return;
  polling = true;
  const id = activeJob;
  try {
    const job = await api('/api/speech/jobs/' + encodeURIComponent(id));
    rememberJob(job); renderJobMenu();
    if (selectedJob === id) renderJob(job);
    if (job.status === 'completed') message('Đã tạo xong bản đọc. Nghe và tải các chương ở bên dưới.');
    if (job.status === 'failed') message(job.message || 'Tạo giọng gặp lỗi. Có thể tiếp tục từ đoạn đã lưu.', true);
    if (job.status === 'cancelled') message('Đã dừng và giữ tiến độ. Chọn bản đọc rồi bấm Tiếp tục khi cần.');
  } catch (e) { message('Mất kết nối theo dõi. Tool sẽ thử lại; không đóng cửa sổ chạy chương trình. ' + e.message, true); }
  finally { polling = false; update(); if (activeJob) schedulePoll(1200); }
}
async function startJob(benchmark = false) {
  recount();
  if (isBusy() || saving) return;
  const blocker = generationBlocker(!benchmark);
  if (blocker) { message(blocker, true); return; }
  const payload = {voice: selected(), speed: Number($('speed').value), quality: $('quality').value, style: $('style').value};
  if (!benchmark) payload.text = $('text').value;
  submitting = true; update(); message(benchmark ? 'Đang đo tốc độ bằng một câu ngắn. Lượt đầu có thể cần nạp mô hình.' : 'Đang chuẩn bị bản đọc. Các đoạn đã xong sẽ được lưu để tiếp tục khi cần.');
  try {
    const job = await api(benchmark ? '/api/benchmark' : '/api/speech/jobs', {method: 'POST', body: JSON.stringify(payload)});
    if (benchmark) job.benchmark = true;
    rememberJob(job); selectedJob = job.id; renderJob(job); $('recordings').scrollIntoView({behavior: 'smooth', block: 'nearest'});
    if (activeJob) schedulePoll(300);
  } catch (e) { message(e.message, true); }
  finally { submitting = false; update(); }
}

document.querySelectorAll('input[name="voice"]').forEach(input => input.addEventListener('change', renderVoice));
['reference-start', 'reference-end', 'reference-text'].forEach(id => $(id).addEventListener('input', () => { drafts.set(selected(), readDraft()); update(); }));
$('text').addEventListener('input', () => { clearTimeout(countTimer); fitLongText(); countPending = true; update(); countTimer = setTimeout(recount, 180); });
$('speed').addEventListener('input', () => { $('speed-value').textContent = Number($('speed').value).toLocaleString('vi-VN', {minimumFractionDigits: 1}) + '×'; });
$('quality').addEventListener('change', () => {
  $('quality-note').textContent = {draft: '4 bước để nghe thử nhanh; có thể giảm độ rõ và phát âm.', fast: '8 bước ưu tiên tốc độ. Nghe thử trước khi tạo bản dài.', balanced: '16 bước cân bằng thời gian xử lý và độ rõ.', quality: '32 bước, xử lý lâu hơn. Chất lượng vẫn phụ thuộc mô hình và mẫu.'}[$('quality').value];
});
$('refresh').addEventListener('click', refresh);
$('refresh-jobs').addEventListener('click', () => refreshJobs().catch(e => message(e.message, true)));
$('job-select').addEventListener('change', async () => {
  selectedJob = $('job-select').value;
  renderJob(jobs.get(selectedJob));
  try {
    const id = selectedJob, job = await api('/api/speech/jobs/' + encodeURIComponent(id));
    rememberJob(job); if (selectedJob === id) renderJob(job); if (activeJob) schedulePoll();
  } catch (e) { message(e.message, true); }
});
$('text-file').addEventListener('change', async () => {
  const file = $('text-file').files[0]; if (!file) return;
  try {
    if (file.size > 8 * 1024 * 1024) throw Error('Tệp TXT tối đa 8 MB. Nội dung tối đa 1.000.000 ký tự Unicode.');
    let text;
    try { text = new TextDecoder('utf-8', {fatal: true}).decode(await file.arrayBuffer()).replace(/^\uFEFF/, ''); }
    catch { throw Error('Tệp chưa phải TXT UTF-8 hợp lệ. Lưu lại bằng UTF-8 rồi nhập lại.'); }
    if (countCodepoints(text) > MAX_CHARACTERS) throw Error('Tệp vượt 1.000.000 ký tự. Văn bản đang soạn được giữ nguyên; chia tệp thành các phần nhỏ hơn.');
    $('text').value = text; recount(); message('Đã nhập toàn bộ văn bản từ tệp TXT.');
  } catch (e) { message(e.message, true); }
  finally { $('text-file').value = ''; }
});
function validReference(ref, voice) {
  return voice && Number.isFinite(ref.start) && Number.isFinite(ref.end) && ref.start >= 0 && ref.end - ref.start >= 3 && ref.end - ref.start <= 8 && ref.end <= voice.reference_settings.duration + .001;
}
$('preview-reference').addEventListener('click', async () => {
  const ref = readDraft(), voice = current();
  if (!validReference(ref, voice)) { message('Chọn đoạn dài 3–8 giây nằm trong bản mẫu.', true); return; }
  try { previewEnd = ref.end; $('reference-player').currentTime = ref.start; await $('reference-player').play(); }
  catch { message('Không phát được mẫu. Thử bấm nút phát trên trình nghe.', true); }
});
$('reference-player').addEventListener('timeupdate', () => { if (previewEnd !== null && $('reference-player').currentTime >= previewEnd) { $('reference-player').pause(); previewEnd = null; } });
$('save-reference').addEventListener('click', async () => {
  if (saving || isBusy() || !current()) return;
  const voice = current(), ref = readDraft();
  if (!validReference(ref, voice)) { message('Chọn đoạn dài 3–8 giây nằm trong bản mẫu.', true); return; }
  if (!ref.text.trim()) { message('Nhập đúng lời nói trong đoạn mẫu trước khi lưu.', true); return; }
  saving = true; update();
  try {
    const result = await api(`/api/voices/${voice.id}/reference`, {method: 'PUT', body: JSON.stringify(ref)});
    voices = voices.map(v => v.id === voice.id ? result.voice : v);
    const latest = selected() === voice.id ? readDraft() : drafts.get(voice.id);
    if (equal(latest, ref)) {
      drafts.set(voice.id, {...result.voice.reference_settings});
      if (selected() === voice.id) $('reference-text').value = result.voice.reference_settings.text;
    }
    message('Đã lưu mẫu riêng cho giọng ' + voice.name + '.');
  } catch (e) { message(e.message, true); }
  finally { saving = false; update(); }
});
$('generate').addEventListener('click', () => startJob(false));
$('benchmark').addEventListener('click', () => startJob(true));
$('stop').addEventListener('click', async () => {
  if (!activeJob || stopping) return;
  const id = activeJob; stopping = true; update();
  try {
    const job = await api(`/api/speech/jobs/${encodeURIComponent(id)}/stop`, {method: 'POST'});
    rememberJob(job); if (selectedJob === id) renderJob(job);
    message('Đã gửi yêu cầu dừng và giữ các đoạn hoàn tất.'); if (activeJob) schedulePoll(200);
  } catch (e) { stopping = false; message(e.message, true); }
  finally { update(); }
});
$('resume').addEventListener('click', async () => {
  const id = selectedJob, existing = jobs.get(id);
  if (isBusy() || !existing || !resumableStates.has(existing.status) || !engineReady()) return;
  submitting = true; update();
  try {
    const job = await api(`/api/speech/jobs/${encodeURIComponent(id)}/resume`, {method: 'POST'});
    rememberJob(job); renderJob(job); message('Đang tiếp tục từ các đoạn đã lưu.'); if (activeJob) schedulePoll(200);
  } catch (e) { message(e.message, true); }
  finally { submitting = false; update(); }
});
recount();
Promise.allSettled([refresh(), refreshJobs()]).then(results => { for (const result of results) if (result.status === 'rejected') message(result.reason.message, true); });
