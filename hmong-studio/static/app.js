'use strict';
const $ = id => document.getElementById(id);
const notify = message => { $('notice').textContent = message; };
let buffer = null, audioURL = null, recorder = null, stream = null, context = null, sourceBlob = null, serviceStatus = null;
let projects = [];
let generationBusy = false, transcriptionBusy = false;
try { projects = JSON.parse(localStorage.getItem('hmong-projects') || '[]'); if (!Array.isArray(projects)) projects = []; } catch { notify('Không đọc được dữ liệu cũ. Bạn có thể nhập lại dự án JSON.'); }
function snapshot() { return { version: 1, title: $('title').value, text: $('text').value, dialect: $('dialect').value, voice: $('voice').value, emotion: $('emotion').value, speed: Number($('speed').value) }; }
function applyProject(p) {
  if (!p || p.version !== 1 || typeof p.text !== 'string' || p.text.length > 10000 || typeof p.title !== 'string' || p.title.length > 120 || !['mww','vi','en'].includes(p.dialect) || (p.voice !== undefined && !['model-default','hmong-white-female','hmong-white-male'].includes(p.voice)) || (p.emotion !== undefined && !['neutral','storytelling','warm','cheerful','sad'].includes(p.emotion)) || !Number.isFinite(p.speed) || p.speed < .5 || p.speed > 2) throw Error('Dự án không hợp lệ.');
  $('title').value = p.title; $('text').value = p.text; $('dialect').value = p.dialect; $('voice').value = p.voice || 'model-default'; $('emotion').value = p.emotion || 'neutral'; updateCapabilities(); $('speed').value = p.speed; update();
  buffer = null; sourceBlob = null; $('transcribe').disabled = true; $('transcript').value = ''; $('useTranscript').disabled = true; $('exportTranscript').disabled = true; $('download').disabled = true; $('player').removeAttribute('src');
  if (audioURL) URL.revokeObjectURL(audioURL); audioURL = null;
  $('wave').getContext('2d').clearRect(0,0,$('wave').width,$('wave').height); $('audioInfo').textContent = 'Chưa có bản thu';
  notify('Đã mở kịch bản. Âm thanh không được lưu trong dự án; hãy nhập bản thu riêng.');
}
function updateReference() { $('referencePlayer').src = '/static/voices/' + $('referenceVoice').value + '.mp3'; }
$('referenceVoice').addEventListener('change', updateReference);
function update() { $('count').textContent = `${$('text').value.length.toLocaleString('vi')} / 10.000 ký tự`; $('speedValue').value = `${Number($('speed').value).toFixed(1)}×`; }
$('text').addEventListener('input', update); $('speed').addEventListener('input', update);
function download(blob, ext) {
  const a = document.createElement('a'), url = URL.createObjectURL(blob);
  a.href = url; a.download = ($('title').value.trim() || 'hmong-studio').replace(/[\\/:*?"<>|]/g,'_') + ext; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
$('exportText').onclick = () => download(new Blob([$ ('text').value], {type:'text/plain;charset=utf-8'}), '.txt');
$('exportProject').onclick = () => download(new Blob([JSON.stringify(snapshot(),null,2)],{type:'application/json'}), '.json');
function persist() { localStorage.setItem('hmong-projects', JSON.stringify(projects)); }
function renderProjects() {
  projects = projects.filter(p => p && typeof p.title === 'string' && typeof p.text === 'string' && ['mww','vi','en'].includes(p.dialect));
  $('projectList').replaceChildren();
  if (!projects.length) { $('projectList').textContent = 'Chưa có dự án. Lưu bản đọc đầu tiên của bạn ở phía trên.'; return; }
  projects.forEach((p,i) => {
    const row = document.createElement('div'); row.className = 'project';
    const title = document.createElement('span'); title.textContent = `${p.title || 'Chưa đặt tên'} · ${{mww:'Hmong Trắng',vi:'Tiếng Việt',en:'English'}[p.dialect]} · ${p.voice === 'hmong-white-male' ? 'Nam' : p.voice === 'hmong-white-female' ? 'Nữ' : 'Giọng gốc'}`;
    const open = document.createElement('button'); open.textContent = 'Mở'; open.onclick = () => { if (confirm('Mở dự án này? Nội dung đang sửa và âm thanh hiện tại sẽ được thay thế.')) { try { applyProject(p); } catch(e) { notify(e.message); } } };
    const del = document.createElement('button'); del.textContent = 'Xóa'; del.onclick = () => { if (confirm('Xóa dự án đã lưu này?')) { const old = [...projects]; projects.splice(i,1); try { persist(); renderProjects(); } catch { projects = old; notify('Không thể lưu thay đổi.'); } } };
    row.append(title,open,del); $('projectList').append(row);
  });
}
$('save').onclick = () => { const old = [...projects]; projects.unshift(snapshot()); try { persist(); renderProjects(); notify('Đã lưu kịch bản và thiết lập trên trình duyệt. Hãy tải âm thanh riêng để giữ bản thu.'); } catch { projects = old; notify('Bộ nhớ trình duyệt không khả dụng hoặc đã đầy. Hãy xuất dự án JSON.'); } };
async function readFile(input, limit, callback) {
  const file = input.files[0]; if (!file) return;
  try { if(file.size > limit) throw Error('Tệp vượt giới hạn dung lượng.'); await callback(file); } catch(e) { notify(e.message); } finally { input.value = ''; }
}
$('textFile').onchange = () => readFile($('textFile'), 100000, async f => { const text = await f.text(); if(text.length > 10000) throw Error('Kịch bản tối đa 10.000 ký tự.'); $('text').value = text; update(); });
$('projectFile').onchange = () => readFile($('projectFile'), 200000, async f => { const p = JSON.parse(await f.text()); if(confirm('Nhập dự án sẽ thay nội dung và âm thanh hiện tại. Tiếp tục?')) applyProject(p); });
async function loadAudio(blob) {
  if(blob.size > 50*1024*1024) throw Error('Âm thanh tối đa 50 MB.');
  context ||= new AudioContext();
  const decoded = await context.decodeAudioData(await blob.arrayBuffer());
  if(audioURL) URL.revokeObjectURL(audioURL);
  buffer = decoded; sourceBlob = blob; $('transcribe').disabled = transcriptionBusy; $('transcript').value=''; $('useTranscript').disabled=true; $('exportTranscript').disabled=true; audioURL = URL.createObjectURL(blob); $('player').src = audioURL;
  $('trimStart').value = 0; $('trimEnd').value = buffer.duration.toFixed(3); $('download').disabled = false;
  $('audioInfo').textContent = `${buffer.duration.toFixed(1)} giây · ${buffer.sampleRate} Hz · ${buffer.numberOfChannels} kênh`;
  const canvas = $('wave'); canvas.width = Math.max(300,canvas.clientWidth*2); const ctx = canvas.getContext('2d'), data = buffer.getChannelData(0);
  ctx.clearRect(0,0,canvas.width,100); ctx.strokeStyle = '#547849'; ctx.beginPath();
  for(let x=0; x<canvas.width; x++) { const start=Math.floor(x*data.length/canvas.width), end=Math.max(start+1,Math.floor((x+1)*data.length/canvas.width)); let min=0,max=0; for(let j=start;j<end && j<data.length;j++){min=Math.min(min,data[j]);max=Math.max(max,data[j]);} ctx.moveTo(x,50+min*45);ctx.lineTo(x,50+max*45); } ctx.stroke();
  notify('Âm thanh đã sẵn sàng. Nghe kiểm tra, chọn khoảng cắt rồi xuất WAV.');
}
$('audioFile').onchange = () => readFile($('audioFile'),50*1024*1024, loadAudio);
$('record').onclick = async () => {
  if(recorder?.state === 'recording') { recorder.stop(); return; }
  if(!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) { notify('Trình duyệt không hỗ trợ thu micro. Dùng HTTPS/localhost hoặc nhập tệp âm thanh.'); return; }
  $('record').disabled = true;
  try {
    stream = await navigator.mediaDevices.getUserMedia({audio:true}); const chunks=[]; let bytes=0;
    recorder = new MediaRecorder(stream);
    recorder.ondataavailable = e => { if(e.data.size) { chunks.push(e.data); bytes+=e.data.size; if(bytes >= 45*1024*1024 && recorder.state==='recording') recorder.stop(); } };
    const timer = setTimeout(() => { if(recorder.state==='recording') recorder.stop(); }, 10*60*1000);
    const cleanup = () => { clearTimeout(timer); stream?.getTracks().forEach(t=>t.stop()); $('record').textContent='● Bắt đầu thu'; $('record').disabled=false; };
    recorder.onstop = async () => { cleanup(); try { await loadAudio(new Blob(chunks,{type:recorder.mimeType})); } catch { notify('Không giải mã được bản thu. Thử nhập tệp WAV.'); } };
    recorder.onerror = () => { cleanup(); notify('Thu âm gặp lỗi. Kiểm tra micro và thử lại.'); };
    recorder.start(1000); $('record').textContent='■ Dừng thu'; notify('Đang thu micro… Tự dừng sau 10 phút hoặc khi gần 50 MB.');
  } catch { stream?.getTracks().forEach(t=>t.stop()); notify('Không mở được micro. Kiểm tra quyền truy cập micro của trình duyệt.'); } finally { $('record').disabled=false; }
};
$('download').onclick = () => {
  if(!buffer) return;
  const start=Number($('trimStart').value), end=Number($('trimEnd').value), gain=Number($('gain').value);
  if(!Number.isFinite(start)||!Number.isFinite(end)||!Number.isFinite(gain)||start<0||end<=start||end>buffer.duration+.001||gain<.1||gain>3) { notify('Khoảng cắt phải nằm trong bản thu; điểm cuối lớn hơn điểm đầu. Âm lượng từ 0,1 đến 3.'); return; }
  const a=Math.floor(start*buffer.sampleRate), b=Math.min(buffer.length,Math.floor(end*buffer.sampleRate)), channels=buffer.numberOfChannels, size=(b-a)*channels*2;
  if(size<=0) { notify('Khoảng cắt quá ngắn.'); return; }
  const out=new ArrayBuffer(44+size), view=new DataView(out); const str=(offset,s)=>[...s].forEach((c,i)=>view.setUint8(offset+i,c.charCodeAt(0)));
  str(0,'RIFF');view.setUint32(4,36+size,true);str(8,'WAVE');str(12,'fmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,channels,true);view.setUint32(24,buffer.sampleRate,true);view.setUint32(28,buffer.sampleRate*channels*2,true);view.setUint16(32,channels*2,true);view.setUint16(34,16,true);str(36,'data');view.setUint32(40,size,true);
  const data=Array.from({length:channels},(_,c)=>buffer.getChannelData(c));let offset=44;
  for(let i=a;i<b;i++)for(let c=0;c<channels;c++){const s=Math.max(-1,Math.min(1,data[c][i]*gain));view.setInt16(offset,s<0?s*32768:s*32767,true);offset+=2;}
  download(new Blob([out],{type:'audio/wav'}),'.wav'); notify('Đã xuất WAV theo khoảng cắt. Âm lượng vượt đỉnh được giới hạn để tránh tràn mẫu.');
};
$('generate').onclick = async () => {
  if(!$('text').value.trim()) { notify('Nhập kịch bản Hmong trước.'); return; }
  generationBusy=true; $('generate').disabled=true; notify('Đang tạo giọng… Lần đầu có thể cần tải mô hình.');
  try { const p=snapshot(), r=await fetch('/api/speech',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:p.text,dialect:p.dialect,voice:p.voice,emotion:p.emotion,speed:p.speed})}); if(!r.ok) { let message='Tạo giọng thất bại.'; try {const e=await r.json();if(typeof e.detail==='string')message=e.detail;}catch{} throw Error(message); } if(JSON.stringify(p)!==JSON.stringify(snapshot()))throw Error('Lời hoặc thiết lập đã thay đổi trong lúc tạo giọng. Hãy tạo lại với bản hiện tại.'); await loadAudio(await r.blob()); } catch(e) { notify(e.message); } finally { generationBusy=false; $('generate').disabled=false; }
};
window.addEventListener('beforeunload',()=>stream?.getTracks().forEach(t=>t.stop()));
renderProjects();update();
function updateCapabilities() {
  if(!serviceStatus) return;
  const s=serviceStatus;
  for(const option of $('voice').options) option.disabled=option.value!=='model-default' && !s.cloning;
  if($('voice').selectedOptions[0]?.disabled) $('voice').value='model-default';
  for(const option of $('emotion').options) option.disabled=option.value!=='neutral' && !s.emotions;
  if($('emotion').selectedOptions[0]?.disabled) $('emotion').value='neutral';
  $('capability').textContent = (s.remote_tts ? 'Dịch vụ TTS từ xa đã cấu hình; chất lượng cần kiểm chứng.' : 'MMS cục bộ: giọng gốc, không nhân bản giọng hoặc điều khiển cảm xúc.') + ' ' + (!s.local.dependencies ? 'Chạy install_local_ai.bat để cài AI cục bộ. ' : '') + ($('dialect').value==='mww' && !s.local.tts_models.mww && !s.remote_tts ? 'Chưa có mô hình TTS Hmong Trắng được xác minh.' : '');
  $('generate').disabled=generationBusy;
}
$('dialect').addEventListener('change',updateCapabilities);
$('transcribe').onclick = async () => {
  if(!sourceBlob) { notify('Thu hoặc nhập âm thanh trước.'); return; }
  transcriptionBusy=true; $('transcribe').disabled=true; const capturedAudio=sourceBlob, capturedLanguage=$('dialect').value; notify('Đang nhận dạng… Lần đầu có thể cần tải mô hình lớn.');
  try {
    const r=await fetch('/api/transcribe?language='+encodeURIComponent($('dialect').value),{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:sourceBlob});
    const data=await r.json(); if(!r.ok)throw Error(typeof data.detail==='string'?data.detail:'Nhận dạng thất bại.');
    if(capturedAudio!==sourceBlob || capturedLanguage!==$('dialect').value)throw Error('Âm thanh hoặc ngôn ngữ đã thay đổi. Nhận dạng lại bản hiện tại.');
    $('transcript').value=data.text; $('useTranscript').disabled=false; $('exportTranscript').disabled=false; notify(data.warning);
  } catch(e) { notify(e.message); } finally { transcriptionBusy=false; $('transcribe').disabled=!sourceBlob; }
};
$('useTranscript').onclick = () => { const text=$('transcript').value; if(text.length>10000){notify('Kết quả vượt 10.000 ký tự. Chọn đoạn ngắn hơn hoặc xuất TXT.');return;} if($('text').value && !confirm('Thay kịch bản hiện tại bằng kết quả nhận dạng?'))return; $('text').value=text;update();notify('Đã đưa lời nhận dạng vào kịch bản. Kiểm tra từ và dấu trước khi tạo giọng.'); };
$('exportTranscript').onclick = () => download(new Blob([$('transcript').value],{type:'text/plain;charset=utf-8'}),'-nhan-dang.txt');
fetch('/api/status').then(r=>{if(!r.ok)throw Error();return r.json();}).then(s=>{serviceStatus=s;notify(s.message);updateCapabilities();}).catch(()=>notify('Không kết nối được máy chủ. Thu âm và nhập tệp vẫn dùng được.'));

$('loadExample').onclick = async () => { try { if($('text').value && !confirm('Thay lời đang sửa bằng kịch bản Hmong mẫu?'))return; const r=await fetch('/static/example-hmong.txt');if(!r.ok)throw Error('Không tải được kịch bản mẫu.');$('text').value=await r.text();$('dialect').value='mww';update();updateCapabilities();notify('Đã nạp lời Hmong do bạn cung cấp. Lời này không phải bản chép của hai mẫu giọng.'); }catch(e){notify(e.message);} };
