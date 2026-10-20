'use strict';
const $ = id => document.getElementById(id);
const notify = message => { $('notice').textContent = message; };
let buffer = null, audioURL = null, recorder = null, stream = null, context = null, sourceBlob = null, serviceStatus = null;
let projects = [];
let generationBusy = false, transcriptionBusy = false, exportBusy = false;
let profiles = [], voiceCatalog = [], cloningAvailable = false, profileSampleBlob = null, referencePreviewEnd = null;
try { projects = JSON.parse(localStorage.getItem('hmong-projects') || '[]'); if (!Array.isArray(projects)) projects = []; } catch { notify('Không đọc được dữ liệu cũ. Bạn có thể nhập lại dự án JSON.'); }
function snapshot() { return { version: 1, title: $('title').value, text: $('text').value, dialect: $('dialect').value, voice: $('voice').value, emotion: $('emotion').value, speed: Number($('speed').value), profile_id: $('profile').value || null }; }
function applyProject(p) {
  if (p?.profile_id != null && (typeof p.profile_id !== 'string' || !/^[A-Za-z0-9_-]{1,80}$/.test(p.profile_id))) throw Error('Hồ sơ giọng không hợp lệ.');
  if (!p || p.version !== 1 || typeof p.text !== 'string' || p.text.length > 10000 || typeof p.title !== 'string' || p.title.length > 120 || !['mww','vi','en'].includes(p.dialect) || (p.voice !== undefined && !['model-default','hmong-white-female','hmong-white-male'].includes(p.voice)) || (p.emotion !== undefined && !['neutral','storytelling','warm','cheerful','sad'].includes(p.emotion)) || !Number.isFinite(p.speed) || p.speed < .5 || p.speed > 2) throw Error('Dự án không hợp lệ.');
  $('title').value = p.title; $('text').value = p.text; $('dialect').value = p.dialect; $('voice').value = p.voice || 'model-default'; $('emotion').value = p.emotion || 'neutral'; if(p.profile_id && !profiles.some(v=>v.id===p.profile_id) && !Array.from($('profile').options).some(o=>o.value===p.profile_id)) $('profile').add(new Option('Mẫu giọng không có trên máy này',p.profile_id)); $('profile').value=p.profile_id || ''; updateCapabilities(); $('speed').value = p.speed; update();
  buffer = null; sourceBlob = null; $('transcribe').disabled = true; $('transcript').value = ''; $('useTranscript').disabled = true; $('exportTranscript').disabled = true; $('download').disabled = true; $('useCurrentAudio').disabled = true; $('player').removeAttribute('src');
  if (audioURL) URL.revokeObjectURL(audioURL); audioURL = null;
  $('wave').getContext('2d').clearRect(0,0,$('wave').width,$('wave').height); $('audioInfo').textContent = 'Chưa có bản thu';
  notify(p.profile_id && !profiles.some(v=>v.id===p.profile_id) ? 'Đã mở kịch bản; mẫu giọng cá nhân không có trên máy này. Hãy thêm hoặc chọn lại mẫu trước khi tạo giọng.' : 'Đã mở kịch bản. Âm thanh không được lưu trong dự án; hãy nhập bản thu riêng.');
}
function updateReference() {
  referencePreviewEnd=null;
  $('referencePlayer').src='/static/voices/'+$('referenceVoice').value+'.mp3';
  const voice=voiceCatalog.find(v=>v.id===$('referenceVoice').value), settings=voice?.reference_settings || {};
  $('referenceStart').value=settings.start ?? 0; $('referenceEnd').value=settings.end ?? 8; $('referenceText').value=settings.text || '';
  $('referenceInfo').textContent=voice?.generation_configured ? 'Mẫu đã cấu hình để tạo giọng. Hãy nghe kiểm tra kết quả.' : !settings.text ? 'Cần chép lời đúng của đoạn mẫu trước khi nhân bản.' : 'Đã có lời mẫu; bộ nhân bản trên máy chưa sẵn sàng.';
}
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
    const title = document.createElement('span'); title.textContent = `${p.title || 'Chưa đặt tên'} · ${{mww:'Hmong Trắng',vi:'Tiếng Việt',en:'English'}[p.dialect]} · ${p.profile_id ? 'Giọng cá nhân' : p.voice === 'hmong-white-male' ? 'Nam' : p.voice === 'hmong-white-female' ? 'Nữ' : 'Giọng gốc'}`;
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
  $('trimStart').value = 0; $('trimEnd').value = buffer.duration.toFixed(3); $('download').disabled = exportBusy; $('useCurrentAudio').disabled = false;
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
function selectedAudioWav() {
  if(!buffer) throw Error('Thu hoặc nhập âm thanh trước.');
  const start=Number($('trimStart').value), end=Number($('trimEnd').value), gain=Number($('gain').value);
  if(!Number.isFinite(start)||!Number.isFinite(end)||!Number.isFinite(gain)||start<0||end<=start||end>buffer.duration+.001||gain<.1||gain>3) throw Error('Khoảng cắt phải nằm trong bản thu; điểm cuối lớn hơn điểm đầu. Âm lượng từ 0,1 đến 3.');
  const a=Math.floor(start*buffer.sampleRate), b=Math.min(buffer.length,Math.floor(end*buffer.sampleRate)), channels=buffer.numberOfChannels, size=(b-a)*channels*2;
  if(size<=0) throw Error('Khoảng cắt quá ngắn.');
  const out=new ArrayBuffer(44+size), view=new DataView(out); const str=(offset,s)=>[...s].forEach((c,i)=>view.setUint8(offset+i,c.charCodeAt(0)));
  str(0,'RIFF');view.setUint32(4,36+size,true);str(8,'WAVE');str(12,'fmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,channels,true);view.setUint32(24,buffer.sampleRate,true);view.setUint32(28,buffer.sampleRate*channels*2,true);view.setUint16(32,channels*2,true);view.setUint16(34,16,true);str(36,'data');view.setUint32(40,size,true);
  const data=Array.from({length:channels},(_,c)=>buffer.getChannelData(c));let offset=44;
  for(let i=a;i<b;i++)for(let c=0;c<channels;c++){const s=Math.max(-1,Math.min(1,data[c][i]*gain));view.setInt16(offset,s<0?s*32768:s*32767,true);offset+=2;}
  return new Blob([out],{type:'audio/wav'});
}
$('download').onclick = async () => {
  if(exportBusy) return;
  exportBusy=true; $('download').disabled=true;
  try {
    const audio=selectedAudioWav(), format=$('exportFormat').value;
    if(format==='wav') download(audio,'.wav');
    else {
      notify('Đang xuất MP3 trên máy…');
      const form=new FormData(); form.append('audio',audio,'edited.wav'); form.append('format','mp3');
      const r=await fetch('/api/audio/export',{method:'POST',body:form});
      if(!r.ok) throw Error(await responseError(r,'Không xuất được MP3.'));
      download(await r.blob(),'.mp3');
    }
    notify('Đã xuất '+format.toUpperCase()+' theo khoảng cắt và âm lượng đã chọn.');
  } catch(e) { notify(e.message); } finally {exportBusy=false; $('download').disabled=!buffer;}
};
$('generate').onclick = async () => {
  if(!$('text').value.trim()) { notify('Nhập kịch bản Hmong trước.'); return; }
  generationBusy=true; updateCapabilities(); notify('Đang tạo giọng trên máy… Lần đầu có thể cần tải mô hình.');
  try { const p=snapshot(), r=await fetch('/api/speech',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:p.text,dialect:p.dialect,voice:p.voice,emotion:p.emotion,speed:p.speed,profile_id:p.profile_id})}); if(!r.ok) { let message='Tạo giọng thất bại.'; try {const e=await r.json();if(typeof e.detail==='string')message=e.detail;}catch{} throw Error(message); } if(JSON.stringify(p)!==JSON.stringify(snapshot()))throw Error('Lời hoặc thiết lập đã thay đổi trong lúc tạo giọng. Hãy tạo lại với bản hiện tại.'); await loadAudio(await r.blob()); } catch(e) { notify(e.message); } finally { generationBusy=false; updateCapabilities(); }
};
window.addEventListener('beforeunload',()=>stream?.getTracks().forEach(t=>t.stop()));
renderProjects();update();
function updateCapabilities() {
  if(!serviceStatus) return;
  const s=serviceStatus, local=s.local || {}, personal=Boolean($('profile').value);
  for(const option of $('voice').options) option.disabled=false;
  $('voice').disabled=personal;
  for(const option of $('emotion').options) option.disabled=option.value!=='neutral' && !s.emotions;
  if($('emotion').selectedOptions[0]?.disabled) $('emotion').value='neutral';
  const modelConfigured=Boolean(local.tts_models?.[$('dialect').value]);
  $('capability').textContent=s.remote_tts ? 'Máy chủ đang bật bộ xử lý từ xa. Nội dung được gửi đến dịch vụ đó khi tạo giọng.' : !local.dependencies ? 'Chưa cài thư viện AI cục bộ. Xem hướng dẫn cài đặt kèm tool.' : !modelConfigured ? 'Chưa cấu hình mô hình đọc cho ngôn ngữ này.' : 'Mô hình đã được cấu hình. Lần đầu có thể cần tải trọng số; hãy nghe kiểm tra cách đọc và phương ngữ.';
  $('profileCapability').textContent=cloningAvailable ? 'Bộ nhân bản đã cấu hình. Chọn mẫu có quyền sử dụng và nghe kiểm tra kết quả.' : (local.clone_engine?.reason || local.cloning_reason || 'Chưa có bộ nhân bản Hmong Trắng sẵn sàng. Bạn vẫn có thể lưu và nghe mẫu; lưu mẫu không tự tạo giọng AI.');
  $('runtimeStatus').textContent=s.remote_tts ? 'Bộ xử lý từ xa đang bật trong cấu hình máy chủ.' : 'Xử lý trên máy · Không cần API key';
  $('runtimeDetail').textContent='Thư viện AI: '+(local.dependencies ? 'đã cài' : 'chưa cài')+' · FFmpeg: '+(local.ffmpeg ? 'có' : 'chưa có')+' · Mô hình Hmong Trắng: '+(local.tts_models?.mww ? 'đã cấu hình, cần kiểm tra bản đọc' : 'chưa cấu hình')+' · Nhân bản: '+(cloningAvailable ? 'đã cấu hình, cần nghe kiểm tra' : 'chưa sẵn sàng')+(local.clone_engine?.reason ? '. '+local.clone_engine.reason : '');
  const fixedSample=$('voice').value!=='model-default';
  const selectedFixed=voiceCatalog.find(v=>v.id===$('voice').value);
  const ready=personal ? cloningAvailable && profiles.some(v=>v.id===$('profile').value) : fixedSample ? Boolean(selectedFixed?.generation_configured) : Boolean(s.remote_tts || (local.dependencies && modelConfigured));
  $('generate').disabled=generationBusy || !ready;
}
$('profile').addEventListener('change',updateCapabilities);
$('voice').addEventListener('change',updateCapabilities);
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
async function responseError(response,fallback) {
  try {const data=await response.json(); return typeof data.detail==='string' ? data.detail : fallback;} catch {return fallback;}
}
async function refreshStatus() {
  $('refreshStatus').disabled=true;
  try {
    const r=await fetch('/api/status'); if(!r.ok) throw Error('Không kiểm tra được bộ xử lý.');
    serviceStatus=await r.json();
    await Promise.all([refreshProfiles(),refreshVoiceCatalog()]); updateCapabilities();
  } catch(e) {notify(e.message); $('runtimeStatus').textContent='Không kết nối được máy chủ.';}
  finally {$('refreshStatus').disabled=false;}
}
$('refreshStatus').onclick=refreshStatus;
async function refreshVoiceCatalog() {
  const r=await fetch('/api/voices');if(!r.ok)throw Error(await responseError(r,'Không đọc được thiết lập mẫu giọng.'));
  const data=await r.json();voiceCatalog=Array.isArray(data.voices)?data.voices:[];updateReference();updateCapabilities();
}
function referenceSelection() {
  const start=Number($('referenceStart').value),end=Number($('referenceEnd').value);
  if(!Number.isFinite(start)||!Number.isFinite(end)||start<0||end-start<3||end-start>8)throw Error('Chọn khoảng mẫu từ 3 đến 8 giây.');
  const duration=$('referencePlayer').duration;
  if(Number.isFinite(duration)&&end>duration+.001)throw Error('Điểm kết thúc vượt thời lượng mẫu.');
  return {start,end,text:$('referenceText').value.trim()};
}
$('previewReference').onclick=async()=>{try{const selection=referenceSelection();$('referencePlayer').currentTime=selection.start;referencePreviewEnd=selection.end;await $('referencePlayer').play();}catch(e){notify(e.message);}};
$('referencePlayer').addEventListener('timeupdate',()=>{if(referencePreviewEnd!==null&&$('referencePlayer').currentTime>=referencePreviewEnd){$('referencePlayer').pause();referencePreviewEnd=null;}});
$('saveReference').onclick=async()=>{
  $('saveReference').disabled=true;
  try {
    const selection=referenceSelection();if(!selection.text)throw Error('Nhập đúng lời nói trong đoạn mẫu trước khi lưu.');
    const r=await fetch('/api/voices/'+encodeURIComponent($('referenceVoice').value)+'/reference',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(selection)});
    if(!r.ok)throw Error(await responseError(r,'Không lưu được thiết lập mẫu.'));
    await refreshVoiceCatalog();notify('Đã lưu đoạn và lời tham chiếu trên máy. Bộ nhân bản còn cần mô hình phù hợp.');
  }catch(e){notify(e.message);}finally{$('saveReference').disabled=false;}
};
async function refreshProfiles() {
  const r=await fetch('/api/profiles'); if(!r.ok) throw Error(await responseError(r,'Không tải được thư viện giọng.'));
  const data=await r.json(); profiles=Array.isArray(data.profiles) ? data.profiles : []; cloningAvailable=data.cloning_available===true;
  const selected=$('profile').value; $('profile').replaceChildren(new Option('Không dùng mẫu cá nhân',''));
  for(const profile of profiles) $('profile').add(new Option(profile.name,profile.id));
  if(selected && !profiles.some(p=>p.id===selected)) $('profile').add(new Option('Mẫu giọng không có trên máy này',selected));
  $('profile').value=selected;
  renderProfiles(); updateCapabilities();
}
function renderProfiles() {
  $('profileList').replaceChildren();
  if(!profiles.length) {$('profileList').textContent='Chưa có giọng cá nhân. Thêm mẫu đầu tiên ở phía trên.'; return;}
  for(const profile of profiles) {
    const card=document.createElement('article'); card.className='voice-card';
    const heading=document.createElement('h3'); heading.textContent=profile.name;
    const details=document.createElement('p'); details.className='muted'; details.textContent='Hmong Trắng · '+Number(profile.duration || 0).toFixed(1)+' giây · Mẫu tham chiếu';
    const audio=document.createElement('audio'); audio.controls=true; audio.preload='none'; audio.src='/api/profiles/'+encodeURIComponent(profile.id)+'/audio'; audio.setAttribute('aria-label','Nghe mẫu '+profile.name);
    const actions=document.createElement('div'); actions.className='actions';
    const select=document.createElement('button'); select.textContent='Chọn giọng'; select.onclick=()=>{$('profile').value=profile.id; $('dialect').value='mww'; updateCapabilities(); notify(cloningAvailable ? 'Đã chọn '+profile.name+'. Nhập lời rồi tạo giọng.' : 'Đã chọn mẫu. Cần cài bộ AI hỗ trợ nhân bản Hmong Trắng để tạo lời mới.');};
    const remove=document.createElement('button'); remove.textContent='Xóa mẫu'; remove.onclick=async()=>{if(!confirm('Xóa hồ sơ và mẫu giọng '+profile.name+' trên máy?'))return; remove.disabled=true; try {const r=await fetch('/api/profiles/'+encodeURIComponent(profile.id),{method:'DELETE'});if(!r.ok)throw Error(await responseError(r,'Không xóa được mẫu.'));await refreshProfiles();notify('Đã xóa mẫu giọng.');}catch(e){notify(e.message);}finally{remove.disabled=false;}};
    actions.append(select,remove); card.append(heading,details,audio,actions); $('profileList').append(card);
  }
}
$('profileAudio').onchange=()=>{profileSampleBlob=null; $('profileAudio').required=true; $('profileUploadInfo').textContent=$('profileAudio').files[0]?.name || 'Chọn mẫu giọng để lưu trên máy.';};
$('useCurrentAudio').onclick=()=>{if(!sourceBlob)return; try {profileSampleBlob=selectedAudioWav();$('profileAudio').value='';$('profileAudio').required=false;$('profileUploadInfo').textContent='Sẽ dùng khoảng cắt và âm lượng hiện tại từ bàn biên tập.';}catch(e){notify(e.message);}};
$('profileForm').onsubmit=async event=>{
  event.preventDefault(); const audio=profileSampleBlob || $('profileAudio').files[0];
  if(!audio){notify('Chọn hoặc thu mẫu giọng trước.');return;}
  if(!$('profileConsent').checked){notify('Xác nhận quyền sử dụng giọng trước khi lưu mẫu.');return;}
  $('saveProfile').disabled=true;
  try {
    const form=new FormData();form.append('audio',audio,audio.name || 'reference.wav');form.append('name',$('profileName').value.trim());form.append('transcript',$('profileTranscript').value);form.append('consent','true');
    const r=await fetch('/api/profiles',{method:'POST',body:form});if(!r.ok)throw Error(await responseError(r,'Không lưu được mẫu giọng.'));
    const saved=await r.json(); await refreshProfiles();$('profile').value=saved.id || saved.profile?.id || '';updateCapabilities();$('profileForm').reset();profileSampleBlob=null;$('profileAudio').required=true;$('profileUploadInfo').textContent='Đã lưu mẫu trên máy. Có thể thêm mẫu khác.';notify('Đã thêm hồ sơ giọng. Lưu mẫu không huấn luyện mô hình; khả năng tạo lời mới phụ thuộc bộ AI.');
  } catch(e){notify(e.message);} finally{$('saveProfile').disabled=false;}
};
refreshStatus();

$('loadExample').onclick = async () => { try { if($('text').value && !confirm('Thay lời đang sửa bằng kịch bản Hmong mẫu?'))return; const r=await fetch('/static/example-hmong.txt');if(!r.ok)throw Error('Không tải được kịch bản mẫu.');$('text').value=await r.text();$('dialect').value='mww';update();updateCapabilities();notify('Đã nạp lời Hmong do bạn cung cấp. Lời này không phải bản chép của hai mẫu giọng.'); }catch(e){notify(e.message);} };
