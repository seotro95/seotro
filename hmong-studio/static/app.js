'use strict';
const $ = id => document.getElementById(id);
const notify = message => { $('notice').textContent = message; };
let buffer = null, audioURL = null, recorder = null, stream = null, context = null;
let projects = [];
try { projects = JSON.parse(localStorage.getItem('hmong-projects') || '[]'); if (!Array.isArray(projects)) projects = []; } catch { notify('Không đọc được dữ liệu cũ. Bạn có thể nhập lại dự án JSON.'); }
function snapshot() { return { version: 1, title: $('title').value, text: $('text').value, dialect: $('dialect').value, voice: $('voice').value, speed: Number($('speed').value) }; }
function applyProject(p) {
  if (!p || p.version !== 1 || typeof p.text !== 'string' || p.text.length > 10000 || typeof p.title !== 'string' || p.title.length > 120 || p.dialect !== 'mww' || (p.voice !== undefined && !['hmong-white-female','hmong-white-male'].includes(p.voice)) || !Number.isFinite(p.speed) || p.speed < .5 || p.speed > 2) throw Error('Dự án không hợp lệ.');
  $('title').value = p.title; $('text').value = p.text; $('dialect').value = p.dialect; $('voice').value = p.voice || 'hmong-white-female'; updateReference(); $('speed').value = p.speed; update();
  buffer = null; $('download').disabled = true; $('player').removeAttribute('src');
  if (audioURL) URL.revokeObjectURL(audioURL); audioURL = null;
  $('wave').getContext('2d').clearRect(0,0,$('wave').width,$('wave').height); $('audioInfo').textContent = 'Chưa có bản thu';
  notify('Đã mở kịch bản. Âm thanh không được lưu trong dự án; hãy nhập bản thu riêng.');
}
function updateReference() { $('referencePlayer').src = '/static/voices/' + $('voice').value + '.mp3'; }
$('voice').addEventListener('change', updateReference);
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
  projects = projects.filter(p => p && typeof p.title === 'string' && typeof p.text === 'string' && p.dialect === 'mww');
  $('projectList').replaceChildren();
  if (!projects.length) { $('projectList').textContent = 'Chưa có dự án. Lưu bản đọc đầu tiên của bạn ở phía trên.'; return; }
  projects.forEach((p,i) => {
    const row = document.createElement('div'); row.className = 'project';
    const title = document.createElement('span'); title.textContent = `${p.title || 'Chưa đặt tên'} · Hmong Trắng · ${p.voice === 'hmong-white-male' ? 'Nam' : 'Nữ'}`;
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
  buffer = decoded; audioURL = URL.createObjectURL(blob); $('player').src = audioURL;
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
  $('generate').disabled=true; notify('Đang tạo giọng Hmong…');
  try { const p=snapshot(), r=await fetch('/api/speech',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:p.text,dialect:p.dialect,voice:p.voice,speed:p.speed})}); if(!r.ok) { let message='Tạo giọng thất bại.'; try {const e=await r.json();if(typeof e.detail==='string')message=e.detail;}catch{} throw Error(message); } await loadAudio(await r.blob()); } catch(e) { notify(e.message); } finally { $('generate').disabled=false; }
};
window.addEventListener('beforeunload',()=>stream?.getTracks().forEach(t=>t.stop()));
renderProjects();update();
fetch('/api/status').then(r=>{if(!r.ok)throw Error();return r.json();}).then(s=>{notify(s.message);$('generate').disabled=!s.tts_configured;}).catch(()=>notify('Không kết nối được máy chủ. Thu âm và nhập tệp vẫn dùng được.'));
