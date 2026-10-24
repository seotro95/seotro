'use strict';
const $ = id => document.getElementById(id);
let voices = [], status = null, displayedVoice = null, activeJob = null, busy = false, saving = false, audioURL = null, previewEnd = null;
const drafts = new Map();
const selected = () => document.querySelector('input[name="voice"]:checked').value;
const current = () => voices.find(v => v.id === selected());
const readDraft = () => ({start: Number($('reference-start').value), end: Number($('reference-end').value), text: $('reference-text').value});
const equal = (a, b) => a && b && a.start === b.start && a.end === b.end && a.text.trim() === b.text.trim();
const message = (text, error = false) => { $('notice').textContent = text; $('notice').classList.toggle('error', error); };

async function api(url, options = {}) {
  const r = await fetch(url, {...options, headers: {'Content-Type': 'application/json', ...options.headers}, cache: 'no-store'});
  let data;
  try { data = await r.json(); } catch { throw Error('Không đọc được phản hồi. Giữ cửa sổ MO_HMONG_NHANH.bat mở và thử lại.'); }
  if (!r.ok) throw Error(typeof data.detail === 'string' ? data.detail : 'Dữ liệu chưa hợp lệ. Kiểm tra văn bản và đoạn mẫu.');
  return data;
}

function update() {
  const voice = current();
  const dirty = voice && !equal(readDraft(), voice.reference_settings);
  $('count').textContent = $('text').value.length.toLocaleString('vi-VN');
  $('generate').disabled = busy || saving || !$('text').value.trim() || $('text').value.length > 2000 || !status?.ready || !voice?.generation_configured || dirty;
  $('generate').textContent = busy ? 'Đang tạo giọng…' : 'Tạo giọng nói';
  $('stop').disabled = !activeJob || !busy;
  $('voice-state').textContent = dirty ? 'Đoạn mẫu có thay đổi chưa lưu.' : voice?.generation_configured ? `Giọng ${voice.name} đã có mẫu và sẵn sàng tạo lời đọc.` : voice?.reason || 'Đang tải mẫu giọng…';
  $('reference-state').textContent = dirty ? 'Chưa lưu thay đổi.' : voice?.reference_ready ? 'Đã lưu riêng cho giọng này.' : 'Chưa có lời tham chiếu.';
  for (const node of document.querySelectorAll('input[name="voice"],#text,#text-file,#speed,#reference-start,#reference-end,#reference-text')) node.disabled = busy;
  $('save-reference').disabled = saving || busy || !voice;
}

function renderVoice() {
  if (displayedVoice) drafts.set(displayedVoice, readDraft());
  const voice = current();
  if (!voice) return;
  displayedVoice = voice.id;
  const ref = drafts.get(voice.id) || voice.reference_settings;
  $('reference-player').pause(); previewEnd = null;
  $('reference-player').src = voice.reference;
  $('reference-start').value = ref.start;
  $('reference-end').value = ref.end;
  $('reference-start').max = $('reference-end').max = voice.reference_settings.duration;
  $('reference-text').value = ref.text;
  $('reference-name').textContent = voice.name;
  $('save-reference').textContent = 'Lưu mẫu cho giọng ' + voice.name;
  if (!voice.reference_ready) $('reference-panel').open = true;
  update();
}

async function refresh() {
  $('refresh').disabled = true;
  try {
    const [state, list] = await Promise.all([api('/api/status'), api('/api/voices')]);
    status = state; voices = list.voices;
    $('engine-state').classList.toggle('ready', state.ready);
    $('engine-state').textContent = state.engine.ready ? 'Bộ tạo giọng đã có trên máy. Chuẩn bị mẫu một lần cho từng giọng, sau đó nhập văn bản để đọc.' : state.engine.reason;
    renderVoice();
  } catch (e) { status = null; update(); message(e.message, true); }
  finally { $('refresh').disabled = false; }
}

document.querySelectorAll('input[name="voice"]').forEach(input => input.addEventListener('change', renderVoice));
['reference-start', 'reference-end', 'reference-text'].forEach(id => $(id).addEventListener('input', () => { drafts.set(selected(), readDraft()); update(); }));
$('text').addEventListener('input', update);
$('speed').addEventListener('input', () => { $('speed-value').textContent = Number($('speed').value).toLocaleString('vi-VN', {minimumFractionDigits: 1}) + '×'; });
$('refresh').addEventListener('click', refresh);

$('text-file').addEventListener('change', async () => {
  const file = $('text-file').files[0];
  if (!file) return;
  try {
    if (file.size > 100000) throw Error('Tệp quá lớn. Mỗi lượt nhận tối đa 2.000 ký tự.');
    const text = (await file.text()).replace(/^\uFEFF/, '');
    if (text.length > 2000) throw Error('Tệp vượt 2.000 ký tự. Chia thành các đoạn ngắn rồi nhập lại.');
    $('text').value = text; update(); message('Đã nhập văn bản.');
  } catch (e) { message(e.message, true); }
  finally { $('text-file').value = ''; }
});

$('preview-reference').addEventListener('click', async () => {
  const ref = readDraft(), voice = current();
  if (!voice || !Number.isFinite(ref.start) || !Number.isFinite(ref.end) || ref.start < 0 || ref.end - ref.start < 3 || ref.end - ref.start > 8 || ref.end > voice.reference_settings.duration) { message('Chọn đoạn dài 3–8 giây nằm trong bản mẫu.', true); return; }
  try { previewEnd = ref.end; $('reference-player').currentTime = ref.start; await $('reference-player').play(); }
  catch { message('Không phát được mẫu. Thử bấm nút phát trên trình nghe.', true); }
});
$('reference-player').addEventListener('timeupdate', () => { if (previewEnd !== null && $('reference-player').currentTime >= previewEnd) { $('reference-player').pause(); previewEnd = null; } });

$('save-reference').addEventListener('click', async () => {
  if (saving || busy || !current()) return;
  const voice = current(), ref = readDraft();
  if (!ref.text.trim()) { message('Nhập đúng lời nói trong đoạn mẫu trước khi lưu.', true); return; }
  saving = true; update();
  try {
    const result = await api(`/api/voices/${voice.id}/reference`, {method: 'PUT', body: JSON.stringify(ref)});
    voices = voices.map(v => v.id === voice.id ? result.voice : v);
    // Keep edits made while the save was running, including edits to the other voice.
    const latest = selected() === voice.id ? readDraft() : drafts.get(voice.id);
    if (equal(latest, ref)) drafts.set(voice.id, {...result.voice.reference_settings});
    message('Đã lưu mẫu riêng cho giọng ' + voice.name + '.');
  } catch (e) { message(e.message, true); }
  finally { saving = false; update(); }
});

$('generate').addEventListener('click', async () => {
  if (busy || $('generate').disabled) return;
  const voice = current(), payload = {text: $('text').value, voice: voice.id, speed: Number($('speed').value)};
  busy = true; update(); message('Đang nạp mô hình và tạo giọng ' + voice.name + '… Có thể bấm Dừng.');
  try {
    let job = await api('/api/speech/jobs', {method: 'POST', body: JSON.stringify(payload)});
    activeJob = job.id; update();
    while (job.status === 'running') {
      await new Promise(resolve => setTimeout(resolve, 700));
      job = await api('/api/speech/jobs/' + activeJob);
    }
    if (job.status === 'cancelled') { message('Đã dừng. Bản thu trước vẫn được giữ.'); return; }
    if (job.status !== 'completed') throw Error(job.message || 'Chưa tạo được bản đọc.');
    const response = await fetch(`/api/speech/jobs/${activeJob}/audio`, {cache: 'no-store'});
    if (!response.ok) throw Error('Không tải được bản đọc vừa tạo.');
    const blob = await response.blob();
    if (!blob.size) throw Error('Bản đọc rỗng.');
    if (audioURL) URL.revokeObjectURL(audioURL);
    audioURL = URL.createObjectURL(blob);
    $('player').src = audioURL; $('download').href = audioURL;
    $('download').download = `hmong-${voice.gender}.wav`;
    $('result-voice').textContent = `Giọng ${voice.name} · ${payload.speed.toLocaleString('vi-VN')}×`;
    $('result').hidden = false;
    message('Đã tạo âm thanh. Bấm phát để nghe hoặc Tải WAV.');
    try { await $('player').play(); } catch { /* The user can play with the native controls. */ }
  } catch (e) { message(e.message, true); }
  finally { activeJob = null; busy = false; update(); }
});
$('stop').addEventListener('click', async () => {
  if (!activeJob) return;
  $('stop').disabled = true;
  try { await api(`/api/speech/jobs/${activeJob}/stop`, {method: 'POST'}); message('Đã gửi yêu cầu dừng.'); }
  catch (e) { message(e.message, true); update(); }
});
refresh();
