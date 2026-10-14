'use strict';
const $ = id => document.getElementById(id);
const state = {assets: [], jobs: [], selected: new Set(), filter: 'all', batch: [], config: {}, health: {}};
const labels = {library: ['Thư viện', 'Mọi ý tưởng bắt đầu<br>từ một video.', 'Nhập nội dung và biến ý tưởng thành video hoàn chỉnh.'], subtitle: ['Phụ đề', 'Mỗi câu nói.<br>Một dòng phụ đề.', 'Tạo, dịch và hoàn thiện phụ đề theo nhịp video của bạn.'], voice: ['Giọng đọc', 'Kể câu chuyện<br>bằng giọng của bạn.', 'Biến kịch bản thành âm thanh và chuẩn bị phần lồng tiếng.'], render: ['Xuất video', 'Hoàn thiện.<br>Và sẵn sàng chia sẻ.', 'Ghép các thành phần, chọn chất lượng và xuất video mới.'], ai: ['Trợ lý AI', 'Ý tưởng mới.<br>Góc nhìn mới.', 'Một người cộng tác cho kịch bản và nội dung của bạn.']};
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const fileUrl = id => '/api/assets/' + encodeURIComponent(id) + '/file';
let toastTimer;
function toast(message, error = false) {
  $('toast').textContent = message; $('toast').className = 'toast' + (error ? ' error' : ''); $('toast').hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => {$('toast').hidden = true;}, error ? 10000 : 5000);
}
async function api(path, options = {}) {
  const response = await fetch(path, options);
  const result = await response.json();
  if (!response.ok) {
    const detail = result.detail;
    throw new Error(Array.isArray(detail) ? detail.map(d => d.msg).join(' · ') : detail || 'Không thực hiện được yêu cầu.');
  }
  return result;
}
const post = (path, body) => api(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
async function work(button, action) {
  if (button) button.disabled = true;
  try { await action(); } catch (error) { toast(error.message, true); }
  finally { if (button) button.disabled = false; }
}
function showTab(tab, preserveBatch = false) {
  if (!preserveBatch) state.batch = [];
  document.querySelectorAll('.nav-item').forEach(b => {b.classList.toggle('active', b.dataset.tab === tab); b.setAttribute('aria-current', b.dataset.tab === tab ? 'page' : 'false');});
  document.querySelectorAll('.panel-view').forEach(v => v.classList.toggle('active', v.id === 'view-' + tab));
  $('page-label').textContent = labels[tab][0]; $('page-title').innerHTML = labels[tab][1]; $('page-description').textContent = labels[tab][2];
  $('render-source').disabled = state.batch.length > 0;
  $('render-batch-note').textContent = state.batch.length ? 'Xuất ' + state.batch.length + ' video đã chọn với cùng cấu hình. Tệp nguồn được giữ nguyên.' : 'Xuất MP4. Tệp nguồn và phụ đề gốc được giữ nguyên.';
}
document.querySelectorAll('[data-tab]').forEach(b => b.addEventListener('click', () => showTab(b.dataset.tab)));
function duration(value) {
  if (!value) return '';
  const n = Math.round(value), h = Math.floor(n / 3600), m = Math.floor(n % 3600 / 60), s = n % 60;
  return (h ? h + ':' + String(m).padStart(2, '0') : m) + ':' + String(s).padStart(2, '0');
}
function renderLibrary() {
  const visible = state.assets.filter(a => state.filter === 'all' || a.kind === state.filter);
  $('empty-library').hidden = visible.length > 0;
  $('library-grid').innerHTML = visible.map(a => {
    const meta = a.metadata, selected = state.selected.has(a.id), icon = {video: '▷', audio: '♬', subtitle: '▤', text: '✦'}[a.kind];
    const desc = a.kind === 'video' ? (meta.width + ' × ' + meta.height) : a.kind === 'subtitle' ? meta.cues + ' đoạn phụ đề' : a.kind === 'audio' ? 'Âm thanh' : 'Văn bản';
    return `<article class="asset-card ${selected ? 'selected' : ''}"><div class="asset-cover"><input type="checkbox" data-select="${esc(a.id)}" aria-label="Chọn ${esc(a.name)}" ${selected ? 'checked' : ''}>${a.kind === 'video' ? `<video preload="metadata" muted src="${fileUrl(a.id)}#t=0.1" aria-hidden="true"></video>` : `<span class="asset-type-icon">${icon}</span>`}<span class="asset-badge">${esc(duration(meta.duration) || a.kind.toUpperCase())}</span></div><div class="asset-details"><h3 title="${esc(a.name)}">${esc(a.name)}</h3><div class="asset-details-bottom"><small>${esc(desc)}</small><div class="asset-actions"><button data-preview="${esc(a.id)}">Xem</button><a href="${fileUrl(a.id)}" download="${esc(a.name)}">↓ Lưu</a></div></div></div></article>`;
  }).join('');
  $('asset-count').textContent = state.assets.length;
  for (const kind of ['video', 'subtitle', 'audio']) $(kind + '-count').textContent = state.assets.filter(a => a.kind === kind).length;
  $('selection-count').textContent = state.selected.size + ' tệp đã chọn';
  $('select-all').checked = !!visible.length && visible.every(a => state.selected.has(a.id));
  $('select-all').indeterminate = visible.some(a => state.selected.has(a.id)) && !$('select-all').checked;
}
$('library-grid').addEventListener('change', e => {
  const id = e.target.dataset.select; if (!id) return;
  if (e.target.checked) state.selected.add(id); else state.selected.delete(id);
  renderLibrary();
});
$('select-all').addEventListener('change', e => {
  state.assets.filter(a => state.filter === 'all' || a.kind === state.filter).forEach(a => {if (e.target.checked) state.selected.add(a.id); else state.selected.delete(a.id);});
  renderLibrary();
});
document.querySelectorAll('[data-filter]').forEach(b => b.addEventListener('click', () => {
  state.filter = b.dataset.filter; document.querySelectorAll('[data-filter]').forEach(f => f.classList.toggle('active', f === b)); renderLibrary();
}));
function populate(id, kinds, emptyLabel) {
  const select = $(id), before = select.value;
  const assets = state.assets.filter(a => kinds.includes(a.kind));
  select.innerHTML = `<option value="">${esc(emptyLabel)}</option>` + assets.map(a => `<option value="${esc(a.id)}">${esc(a.name)}</option>`).join('');
  if (assets.some(a => a.id === before)) select.value = before;
}
function populateForms() {
  populate('stt-source', ['video', 'audio'], 'Chọn video / âm thanh');
  populate('translate-source', ['subtitle'], 'Chọn phụ đề SRT');
  populate('editor-source', ['subtitle'], 'Phụ đề mới');
  populate('render-source', ['video'], 'Chọn video');
  populate('render-subtitle', ['subtitle'], 'Không thêm phụ đề');
  populate('render-audio', ['audio', 'video'], 'Giữ âm thanh gốc');
  populate('ai-result-source', ['text'], 'Chọn bản biên tập');
}
function renderJobs() {
  $('jobs-count').textContent = state.jobs.length + ' tác vụ';
  const statuses = {queued: 'Đang chờ', running: 'Đang xử lý', done: 'Hoàn tất', error: 'Có lỗi', cancelling: 'Đang yêu cầu dừng', cancelled: 'Đã dừng', interrupted: 'Bị gián đoạn'};
  const actions = {render: 'Xuất video', download: 'Tải video', stt: 'Tạo phụ đề', translate: 'Dịch phụ đề', tts: 'Giọng đọc', ai: 'Biên tập AI'};
  $('jobs-list').innerHTML = state.jobs.length ? state.jobs.map(j => `<div class="job-row"><span class="job-icon">${j.status === 'done' ? '✓' : '↗'}</span><div class="job-info"><strong>${esc(j.name)}</strong><small>${esc(j.error || actions[j.action] || j.action)}</small></div><div class="job-results">${(j.result?.asset_ids || []).map(id => `<a href="${fileUrl(id)}" download>↓ Tải kết quả</a>`).join('')}</div><span class="job-state ${esc(j.status)}">${esc(statuses[j.status] || j.status)}</span>${['running','queued'].includes(j.status) ? `<button class="button small secondary" data-cancel="${esc(j.id)}">Dừng</button>` : ''}</div>`).join('') : '<p class="muted">Các tác vụ của bạn sẽ xuất hiện tại đây.</p>';
}
let refreshing = false;
async function refresh() {
  if (refreshing) return;
  refreshing = true;
  try {
    const [assets, jobs] = await Promise.all([api('/api/assets'), api('/api/jobs')]);
    if (JSON.stringify(assets) !== JSON.stringify(state.assets)) {state.assets = assets; renderLibrary(); populateForms();}
    if (JSON.stringify(jobs) !== JSON.stringify(state.jobs)) {state.jobs = jobs; renderJobs();}
  } finally {refreshing = false;}
}
async function queue(path, body) {
  const result = await post(path, body); toast('Đã thêm ' + result.job_ids.length + ' tác vụ vào hàng đợi.'); await refresh();
}
$('jobs-list').addEventListener('click', e => {
  const id = e.target.dataset.cancel;
  if (id) work(e.target, async () => {await post('/api/jobs/' + encodeURIComponent(id) + '/cancel', {}); await refresh();});
});
async function uploadFiles(files) {
  if (!files.length) return;
  const button = $('import-button'); button.disabled = true;
  let imported = 0;
  try {
    for (const file of files) {
      button.textContent = 'Đang nhập ' + (imported + 1) + '/' + files.length;
      const form = new FormData(); form.append('file', file);
      try {await api('/api/upload', {method: 'POST', body: form}); imported++;} catch(e) {toast(file.name + ': ' + e.message, true);}
    }
    await refresh(); if (imported) toast('Đã nhập ' + imported + ' tệp vào thư viện.');
  } finally {button.disabled = false; button.textContent = '＋ Nhập tệp'; $('file-input').value = '';}
}
['import-button', 'empty-import'].forEach(id => $(id).addEventListener('click', () => $('file-input').click()));
$('file-input').addEventListener('change', e => work(null, () => uploadFiles([...e.target.files])));
document.addEventListener('dragover', e => {if (e.dataTransfer.types.includes('Files')) {e.preventDefault(); document.body.classList.add('drag-active');}});
document.addEventListener('dragleave', e => {if (!e.relatedTarget) document.body.classList.remove('drag-active');});
document.addEventListener('drop', e => {e.preventDefault(); document.body.classList.remove('drag-active'); if (e.dataTransfer.files.length) work(null, () => uploadFiles([...e.dataTransfer.files]));});
document.querySelectorAll('[data-close-dialog]').forEach(b => b.addEventListener('click', () => {b.closest('dialog').close(); if (b.closest('dialog').id === 'preview-dialog') $('preview-content').innerHTML = '';}));
$('preview-dialog').addEventListener('close', () => {$('preview-content').innerHTML = '';});
$('open-download').addEventListener('click', () => $('download-dialog').showModal());
$('download-form').addEventListener('submit', e => {e.preventDefault(); work(e.submitter, async () => {
  await queue('/api/download', {urls: $('download-urls').value.split(/\r?\n/).map(s => s.trim()).filter(Boolean)}); $('download-dialog').close();
});});
$('library-grid').addEventListener('click', e => {
  const id = e.target.dataset.preview; if (!id) return;
  work(e.target, async () => {
    const a = state.assets.find(a => a.id === id); $('preview-title').textContent = a.name;
    if (['video', 'audio'].includes(a.kind)) $('preview-content').innerHTML = `<${a.kind} src="${fileUrl(id)}" controls></${a.kind}>`;
    else {const result = await api('/api/assets/' + encodeURIComponent(id) + '/text'); $('preview-content').innerHTML = '<pre>' + esc(result.text) + '</pre>';}
    $('preview-dialog').showModal();
  });
});
$('stt-engine').addEventListener('change', () => {
  const local = $('stt-engine').value === 'local'; $('whisper-model-label').hidden = !local;
  $('stt-help').textContent = local ? 'Cần cài AI cục bộ. Model tải về trong lần chạy đầu; sau đó nhận dạng trên CPU của máy.' : 'Cấu hình API trong Cài đặt AI. Tệp âm thanh sẽ được gửi tới nhà cung cấp bạn chọn.';
});
function sttBody(ids) {return {asset_ids: ids, engine: $('stt-engine').value, language: $('stt-language').value, model: $('whisper-model').value};}
$('stt-form').addEventListener('submit', e => {e.preventDefault(); work(e.submitter, () => queue('/api/stt', sttBody([$('stt-source').value])));});
$('batch-stt').addEventListener('click', e => work(e.target, async () => {
  const ids = state.assets.filter(a => state.selected.has(a.id) && ['video', 'audio'].includes(a.kind)).map(a => a.id);
  if (!ids.length) throw new Error('Chọn ít nhất một video hoặc âm thanh trong thư viện.');
  await queue('/api/stt', sttBody(ids));
}));
$('translate-form').addEventListener('submit', e => {e.preventDefault(); work(e.submitter, () => queue('/api/translate', {asset_ids: [$('translate-source').value], language: $('translate-language').value}));});
$('load-subtitle').addEventListener('click', e => work(e.target, async () => {
  const id = $('editor-source').value; if (!id) {$('srt-editor').value = ''; return;}
  const result = await api('/api/assets/' + encodeURIComponent(id) + '/text'); $('srt-editor').value = result.text;
  $('subtitle-name').value = state.assets.find(a => a.id === id).name.replace(/\.srt$/i, '') + '_sua.srt';
}));
$('save-subtitle').addEventListener('click', e => work(e.target, async () => {
  const result = await post('/api/subtitles', {name: $('subtitle-name').value, text: $('srt-editor').value});
  await refresh(); $('editor-source').value = result.asset_id; toast('Đã lưu phụ đề mới: ' + result.cues + ' đoạn.');
}));
function voiceOptions() {
  const engine = $('tts-engine').value;
  const voices = engine === 'edge' ? [['vi-VN-HoaiMyNeural','Hoài My — tiếng Việt'],['vi-VN-NamMinhNeural','Nam Minh — tiếng Việt'],['en-US-AriaNeural','Aria — tiếng Anh'],['zh-CN-XiaoxiaoNeural','Xiaoxiao — tiếng Trung']] : engine === 'windows' ? [['default','Giọng mặc định Windows']] : [['alloy','Alloy'],['nova','Nova'],['shimmer','Shimmer'],['echo','Echo'],['onyx','Onyx']];
  if (engine === 'api' && state.config.voice && !voices.some(v => v[0] === state.config.voice)) voices.unshift([state.config.voice, state.config.voice]);
  $('tts-voice').innerHTML = voices.map(([value,label]) => `<option value="${esc(value)}">${esc(label)}</option>`).join('');
  $('tts-help').textContent = engine === 'edge' ? 'Cần cài edge-tts và kết nối Internet. Giọng tiếng Việt không cần API key.' : engine === 'windows' ? 'Dùng giọng đã cài trên Windows. Ngôn ngữ phụ thuộc các gói giọng nói trên máy.' : 'API sử dụng key trong Cài đặt AI.';
}
$('tts-engine').addEventListener('change', voiceOptions);
$('tts-form').addEventListener('submit', e => {e.preventDefault(); work(e.submitter, () => queue('/api/tts', {text: $('tts-text').value, engine: $('tts-engine').value, voice: $('tts-voice').value}));});
function previewRender() {
  const id = $('render-source').value;
  $('render-preview').innerHTML = id ? `<video src="${fileUrl(id)}" controls></video>` : 'Chọn video để xem trước';
}
$('render-source').addEventListener('change', previewRender);
$('batch-render').addEventListener('click', () => {
  state.batch = state.assets.filter(a => a.kind === 'video' && state.selected.has(a.id)).map(a => a.id);
  if (!state.batch.length) {toast('Chọn ít nhất một video trong thư viện.', true); return;}
  showTab('render', true); $('render-source').value = state.batch[0]; previewRender();
});
$('render-form').addEventListener('submit', e => {e.preventDefault(); work(e.submitter, () => queue('/api/render', {
  asset_ids: state.batch.length ? state.batch : [$('render-source').value], subtitle_id: $('render-subtitle').value || null,
  audio_id: $('render-audio').value || null, start: Number($('render-start').value), end: $('render-end').value ? Number($('render-end').value) : null,
  speed: Number($('render-speed').value), height: Number($('render-height').value), title: $('render-title').value,
  font_size: Number($('render-font-size').value), subtitle_color: $('render-color').value, crf: Number($('render-crf').value)
}));});
document.querySelectorAll('[data-prompt]').forEach(b => b.addEventListener('click', () => {$('ai-prompt').value = b.dataset.prompt; $('ai-prompt').focus();}));
$('ai-form').addEventListener('submit', e => {e.preventDefault(); work(e.submitter, () => queue('/api/ai', {prompt: $('ai-prompt').value}));});
$('load-ai-result').addEventListener('click', e => work(e.target, async () => {
  if (!$('ai-result-source').value) throw new Error('Chọn một bản biên tập trong thư viện.');
  const result = await api('/api/assets/' + encodeURIComponent($('ai-result-source').value) + '/text'); $('ai-result').textContent = result.text;
}));
async function loadConfig() {
  state.config = await api('/api/config');
  const fields = {'api-base':'base_url', 'chat-model':'chat_model', 'stt-model':'stt_model', 'tts-model':'tts_model', 'config-voice':'voice'};
  Object.entries(fields).forEach(([id,key]) => {$(id).value = state.config[key];});
  $('api-key').value = ''; $('api-key-state').textContent = state.config.key_is_set ? 'Đã có key cho phiên này. Để trống để giữ key hiện tại.' : 'Key chỉ lưu trong bộ nhớ của phiên chạy này. Nhập lại khi mở tool lần sau.';
  voiceOptions();
}
document.querySelectorAll('[data-open-settings]').forEach(b => b.addEventListener('click', () => work(b, async () => {await loadConfig(); $('settings-dialog').showModal();})));
function configBody() {return {base_url: $('api-base').value.trim(), api_key: $('api-key').value.trim() || null, chat_model: $('chat-model').value, stt_model: $('stt-model').value, tts_model: $('tts-model').value, voice: $('config-voice').value};}
$('settings-form').addEventListener('submit', e => {e.preventDefault(); work(e.submitter, async () => {
  await post('/api/config', configBody()); await loadConfig(); $('settings-dialog').close(); toast('Đã áp dụng cấu hình AI cho phiên này.');
});});
$('clear-api-key').addEventListener('click', e => work(e.target, async () => {await post('/api/config', {...configBody(), api_key: null, clear_key: true}); await loadConfig(); toast('Đã xóa key khỏi phiên chạy.');}));
async function initialize() {
  state.health = await api('/api/health'); await loadConfig();
  if (!state.health.ffmpeg || !state.health.ffprobe) {$('setup-note').hidden = false; $('setup-note').textContent = 'Cần FFmpeg và FFprobe để xử lý video. Xem HUONG_DAN.md đi kèm tool.';}
  if (state.health.local_whisper) {$('stt-engine').value = 'local'; $('stt-engine').dispatchEvent(new Event('change'));}
  if (state.health.edge_tts) {$('tts-engine').value = 'edge'; voiceOptions();}
  else if (state.health.windows_tts) {$('tts-engine').value = 'windows'; voiceOptions();}
  await refresh(); renderLibrary(); populateForms();
  setInterval(() => refresh().catch(() => {}), 2000);
}
initialize().catch(e => toast('Không kết nối được tool: ' + e.message, true));
