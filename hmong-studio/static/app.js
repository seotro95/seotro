'use strict';
const $ = id => document.getElementById(id);
const notify = message => { $('notice').textContent = message; };
let buffer = null, audioURL = null, recorder = null, stream = null, context = null, sourceBlob = null, sourceURL = null, sourceDuration = null, sourceExtension = '.wav', serviceStatus = null;
let projects = [];
let generationBusy = false, transcriptionBusy = false, stoppingGeneration = false, generationState = null;
const MAX_SCRIPT_CHARACTERS = 1000000;
try { projects = JSON.parse(localStorage.getItem('hmong-projects') || '[]'); if (!Array.isArray(projects)) projects = []; } catch { notify('Không đọc được dữ liệu cũ. Bạn có thể nhập lại dự án JSON.'); }
function snapshot() { return { version: 1, title: $('title').value, text: $('text').value, input_format: $('inputFormat').value, dialect: $('dialect').value, voice: $('voice').value, emotion: $('emotion').value, speed: Number($('speed').value), compute_mode: $('computeMode').value, cleanup: $('cleanup').value, reference_text: $('presetTranscript').value }; }
function applyProject(p) {
  if (!p || p.version !== 1 || typeof p.text !== 'string' || p.text.length > MAX_SCRIPT_CHARACTERS || typeof p.title !== 'string' || p.title.length > 120 || !['mww','vi','en'].includes(p.dialect) || (p.input_format !== undefined && !['auto','text','srt'].includes(p.input_format)) || (p.compute_mode !== undefined && !['standard','fast'].includes(p.compute_mode)) || (p.cleanup !== undefined && !['off','light','strong'].includes(p.cleanup)) || (p.voice !== undefined && !['model-default','hmong-white-female','hmong-white-male'].includes(p.voice) && !/^custom-[a-f0-9]{32}$/.test(p.voice)) || (p.emotion !== undefined && !['neutral','storytelling','warm','cheerful','sad','review','advertising','news','meditation'].includes(p.emotion)) || (p.reference_text !== undefined && (typeof p.reference_text !== 'string' || p.reference_text.length>2000)) || !Number.isFinite(p.speed) || p.speed < .5 || p.speed > 2) throw Error('Dự án không hợp lệ.');
  if(p.voice?.startsWith('custom-') && ![...$('voice').options].some(o=>o.value===p.voice))throw Error('Mẫu giọng trong dự án không còn trên máy này. Thêm lại mẫu hoặc chọn giọng khác.');
  $('title').value = p.title; $('text').value = p.text; $('inputFormat').value = p.input_format || 'auto'; $('dialect').value = p.dialect; $('voice').value = p.voice || 'model-default'; $('emotion').value = p.emotion || 'review'; $('computeMode').value=p.compute_mode||'standard'; $('cleanup').value=p.cleanup||'light'; updateProcessingOptions(); syncPreset(); if(p.reference_text!==undefined)$('presetTranscript').value=p.reference_text; updateCapabilities(); $('speed').value = p.speed; update();
  buffer = null; sourceBlob = null; sourceURL = null; sourceDuration = null; generationState = null; renderGeneration(); $('transcribe').disabled = true; $('transcript').value = ''; $('useTranscript').disabled = true; $('exportTranscript').disabled = true; $('download').disabled = true; $('fullDownload').disabled = true; $('player').removeAttribute('src');
  if (audioURL) URL.revokeObjectURL(audioURL); audioURL = null;
  $('wave').getContext('2d').clearRect(0,0,$('wave').width,$('wave').height); $('wave').hidden=false; $('audioInfo').textContent = 'Chưa có bản thu'; $('audioEditNote').textContent='Xuất WAV PCM 16-bit theo khoảng đã chọn và âm lượng. Bản thu gốc không bị ghi đè.';
  for(const id of ['trimStart','trimEnd','gain'])$(id).disabled=true;
  notify('Đã mở kịch bản. Âm thanh không được lưu trong dự án; hãy nhập bản thu riêng.');
}
function syncPreset(){
  const builtin=['hmong-white-female','hmong-white-male'].includes($('voice').value);
  $('presetTranscriptPanel').hidden=!builtin || Boolean(serviceStatus?.local_cloning);
  if(builtin){
    $('referenceVoice').value=$('voice').value;
    $('referencePlayer').src='/static/voices/'+$('voice').value+'.mp3';
    try{$('presetTranscript').value=localStorage.getItem('hmong-reference-'+$('voice').value)||'';}catch{$('presetTranscript').value='';}
  }
}
function updateReference() { $('voice').value=$('referenceVoice').value;syncPreset();updateCapabilities(); }
$('presetTranscript').addEventListener('input',()=>{try{localStorage.setItem('hmong-reference-'+$('voice').value,$('presetTranscript').value);}catch{notify('Không lưu được bản chép trên trình duyệt. Hãy xuất dự án JSON.');}});
$('referenceVoice').addEventListener('change', updateReference);
function isSRTInput() { return $('inputFormat').value === 'srt' || ($('inputFormat').value === 'auto' && /\d{2,}:\d{2}:\d{2}[,.]\d{3}\s*-->/.test($('text').value)); }
function update() {
  $('text').maxLength=MAX_SCRIPT_CHARACTERS;
  $('count').textContent = `${$('text').value.length.toLocaleString('vi')} / ${MAX_SCRIPT_CHARACTERS.toLocaleString('vi')} ký tự`;
  $('speedValue').value = `${Number($('speed').value).toFixed(1)}×`;
  $('formatHint').textContent = isSRTInput()
    ? 'SRT: chỉ đọc lời dưới mốc giờ, giữ khoảng lặng và căn WAV theo thời gian. Nếu lời dài hơn một mốc, hãy tăng tốc độ đọc hoặc nới thời gian mốc đó.'
    : 'Nhập lời đọc liên tục hoặc chọn SRT để căn lời theo mốc giờ. Tự nhận dạng nhận cả văn bản thường và SRT.';
  $('exportText').textContent=isSRTInput()?'Xuất SRT ↗':'Xuất TXT ↗';
}
$('text').addEventListener('input', update); $('speed').addEventListener('input', update);
$('inputFormat').addEventListener('change',update);
function updateProcessingOptions(){
  const gpu=String(serviceStatus?.cosy?.device||'').toLowerCase().includes('cuda');
  $('computeHelp').textContent=$('computeMode').value==='fast'
    ? (gpu?'Máy đang dùng GPU. Chế độ Nhanh (CPU) dành cho máy chạy bằng CPU; Studio tiếp tục dùng GPU hiện có.':'Nhanh (CPU) là chế độ thử nghiệm, âm sắc có thể thay đổi. Hãy nghe kiểm tra; chọn Chuẩn khi cần giọng ổn định. Tốc độ thực tế tùy máy.')
    : 'Chuẩn ưu tiên giọng ổn định. Có thể thử Nhanh (CPU) để giảm thời gian tạo trên máy dùng CPU rồi nghe đối chiếu.';
  const cleanupHints={off:'Tắt lọc ồn, giữ nguyên tiếng nền trong mẫu và bản đọc.',light:'Giảm nhẹ tiếng nền trong mẫu giọng và bản đọc. Nên dùng khi cần lời rõ và giữ âm sắc.',strong:'Lọc nhiều hơn trong mẫu giọng và bản đọc, có thể làm mất một số âm nhỏ. Nếu giọng bị mỏng hoặc mất âm, hãy chọn Nhẹ.'};
  $('cleanupHelp').textContent=cleanupHints[$('cleanup').value]+' Lọc ồn không tách được nhạc nền hoặc giọng người khác.';
}
function renderComputeStatus(){
  const runtime=serviceStatus?.cosy, device=String(runtime?.device||'').toLowerCase(), precision=runtime?.precision;
  if(device.includes('cuda')){
    $('computeStatus').textContent='Bộ xử lý: GPU NVIDIA · mô hình được giữ sẵn giữa các lượt tạo.';
  }else if(device.includes('cpu')){
    const actualMode=precision==='float32_int8_flow'?' · chế độ Nhanh':precision==='float32'?' · chế độ Chuẩn':'';
    $('computeStatus').textContent='Bộ xử lý: CPU'+actualMode+' · tốc độ tùy máy và độ dài lời đọc.';
  }else{
    $('computeStatus').textContent='Tốc độ tạo phụ thuộc CPU/GPU và độ dài lời đọc. Lần đầu cần nạp mô hình.';
  }
}
$('computeMode').addEventListener('change',updateProcessingOptions);
$('cleanup').addEventListener('change',updateProcessingOptions);
function download(blob, ext) {
  const a = document.createElement('a'), url = URL.createObjectURL(blob);
  a.href = url; a.download = ($('title').value.trim() || 'hmong-studio').replace(/[\\/:*?"<>|]/g,'_') + ext; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
$('exportText').onclick = () => download(new Blob([$ ('text').value], {type:'text/plain;charset=utf-8'}), isSRTInput()?'.srt':'.txt');
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
$('textFile').onchange = () => readFile($('textFile'), 8*1024*1024, async f => { const text = await f.text(); if(text.length > MAX_SCRIPT_CHARACTERS) throw Error('Kịch bản tối đa 1.000.000 ký tự.'); $('text').value = text; $('inputFormat').value=/\.srt$/i.test(f.name)?'srt':'auto'; update(); notify('Đã nhập kịch bản '+(isSRTInput()?'SRT. Mốc giờ không được đọc thành lời.':'văn bản.')); });
$('projectFile').onchange = () => readFile($('projectFile'), 8*1024*1024, async f => { const p = JSON.parse(await f.text()); if(confirm('Nhập dự án sẽ thay nội dung và âm thanh hiện tại. Tiếp tục?')) applyProject(p); });
function canTranscribe() { return Boolean(sourceBlob && sourceBlob.size<=50*1024*1024 && (sourceDuration===null || sourceDuration<=600)); }
async function loadAudio(blob, options={}) {
  if(blob.size > (options.generated?250:50)*1024*1024) throw Error(options.generated?'Kết quả âm thanh vượt 250 MB.':'Âm thanh nhập vào tối đa 50 MB.');
  const large=blob.size>25*1024*1024;
  let decoded=null;
  if(!large){context ||= new AudioContext();decoded=await context.decodeAudioData(await blob.arrayBuffer());}
  const header=new Uint8Array(await blob.slice(0,12).arrayBuffer());
  const wav=String.fromCharCode(...header.slice(0,4))==='RIFF' && String.fromCharCode(...header.slice(8,12))==='WAVE';
  const extension=wav?'.wav':({'audio/mpeg':'.mp3','audio/mp4':'.m4a','audio/ogg':'.ogg','audio/webm':'.webm'}[blob.type.split(';')[0]]||'.audio');
  if(audioURL) URL.revokeObjectURL(audioURL);
  buffer = decoded; sourceBlob = blob; sourceURL = null; sourceDuration=decoded?.duration??null; sourceExtension=extension; $('transcribe').disabled=transcriptionBusy||!canTranscribe(); $('transcript').value=''; $('useTranscript').disabled=true; $('exportTranscript').disabled=true; audioURL = URL.createObjectURL(blob); $('player').src = audioURL;
  $('trimStart').value = 0; $('trimEnd').value = decoded?decoded.duration.toFixed(3):0; $('download').disabled=!decoded; $('fullDownload').disabled=false; $('fullDownload').textContent=wav?'↓ Tải toàn bộ WAV':'↓ Tải âm thanh gốc';
  for(const id of ['trimStart','trimEnd','gain'])$(id).disabled=!decoded;
  $('wave').hidden=large;
  $('audioEditNote').textContent=large?'Bản dài được phát trực tiếp để tiết kiệm bộ nhớ. Bấm Tải toàn bộ WAV để giữ nguyên âm thanh và các khoảng lặng; công cụ cắt chỉ dùng cho bản ngắn.':'Xuất WAV PCM 16-bit theo khoảng đã chọn và âm lượng. Bản thu gốc không bị ghi đè.';
  const sizeText=`${(blob.size/1024/1024).toFixed(1)} MB`;
  $('audioInfo').textContent = decoded?`${decoded.duration.toFixed(1)} giây · ${decoded.sampleRate} Hz · ${decoded.numberOfChannels} kênh`:`${sizeText} · Phát trực tiếp`;
  $('player').onloadedmetadata=()=>{if(sourceBlob!==blob)return;sourceDuration=Number.isFinite($('player').duration)?$('player').duration:null;$('transcribe').disabled=transcriptionBusy||!canTranscribe();if(large && sourceDuration!==null)$('audioInfo').textContent=`${sourceDuration.toFixed(1)} giây · ${sizeText} · Phát trực tiếp`;};
  if(large){notify('Âm thanh đã sẵn sàng. Nghe trực tiếp hoặc tải toàn bộ WAV; không cần giải mã bản dài trong trình biên tập.');return;}
  const canvas = $('wave'); canvas.width = Math.max(300,canvas.clientWidth*2); const ctx = canvas.getContext('2d'), data = buffer.getChannelData(0);
  ctx.clearRect(0,0,canvas.width,100); ctx.strokeStyle = '#547849'; ctx.beginPath();
  for(let x=0; x<canvas.width; x++) { const start=Math.floor(x*data.length/canvas.width), end=Math.max(start+1,Math.floor((x+1)*data.length/canvas.width)); let min=0,max=0; for(let j=start;j<end && j<data.length;j++){min=Math.min(min,data[j]);max=Math.max(max,data[j]);} ctx.moveTo(x,50+min*45);ctx.lineTo(x,50+max*45); } ctx.stroke();
  notify('Âm thanh đã sẵn sàng. Nghe kiểm tra, chọn khoảng cắt rồi xuất WAV.');
}
function loadAudioURL(url, bytes) {
  if(audioURL)URL.revokeObjectURL(audioURL);audioURL=null;
  buffer=null;sourceBlob=null;sourceURL=url;sourceDuration=null;sourceExtension='.wav';
  $('player').src=url;$('wave').hidden=true;$('transcribe').disabled=true;$('transcript').value='';$('useTranscript').disabled=true;$('exportTranscript').disabled=true;
  for(const id of ['trimStart','trimEnd','gain','download'])$(id).disabled=true;
  $('trimStart').value=0;$('trimEnd').value=0;$('fullDownload').disabled=false;$('fullDownload').textContent='↓ Tải toàn bộ WAV';
  const sizeText=Number.isFinite(bytes)?`${(bytes/1024/1024).toLocaleString('vi',{maximumFractionDigits:1})} MB`:'WAV';
  $('audioInfo').textContent=`${sizeText} · Phát trực tiếp`;
  $('audioEditNote').textContent='Bản dài được phát và tải trực tiếp từ máy chủ để tiết kiệm bộ nhớ. Tải toàn bộ WAV để giữ nguyên lời và các khoảng lặng; công cụ cắt chỉ dùng cho bản ngắn. Hãy tải trước khi đóng Studio hoặc tạo nhiều bản mới.';
  $('player').onloadedmetadata=()=>{if(sourceURL!==url)return;sourceDuration=Number.isFinite($('player').duration)?$('player').duration:null;if(sourceDuration!==null)$('audioInfo').textContent=`${sourceDuration.toFixed(1)} giây · ${sizeText} · Phát trực tiếp`;};
}
$('fullDownload').onclick=()=>{
  if(sourceBlob){download(sourceBlob,sourceExtension);return;}
  if(sourceURL){const link=document.createElement('a');link.href=sourceURL;link.download=($('title').value.trim()||'hmong-studio').replace(/[\\/:*?"<>|]/g,'_')+'.wav';link.click();}
};
$('audioFile').onchange = () => readFile($('audioFile'),50*1024*1024, loadAudio);
let microphoneAttempt=0;
function microphoneMessage(message){$('microphoneStatus').textContent=message;}
function microphoneError(error){
  if(!window.isSecureContext)return 'Trình duyệt chặn micro trên kết nối HTTP này. Trên máy chạy Studio, mở http://127.0.0.1:8090; truy cập từ máy khác cần HTTPS. Bạn vẫn có thể dùng hai mẫu nam/nữ hoặc nhập tệp.';
  const messages={
    NotAllowedError:'Micro chưa được cấp quyền. Trong Chrome/Edge: mở quyền trang ở bên trái thanh địa chỉ, cho phép Micro rồi thử lại. Trong Windows: Cài đặt → Quyền riêng tư và bảo mật → Micro, cho phép ứng dụng máy tính truy cập.',
    PermissionDeniedError:'Quyền micro đã bị từ chối. Cho phép Micro trong quyền trang của trình duyệt và cài đặt quyền riêng tư Windows rồi thử lại.',
    NotFoundError:'Không tìm thấy micro. Cắm micro hoặc chọn đúng thiết bị đầu vào trong Cài đặt âm thanh Windows. Hai mẫu nam/nữ có sẵn vẫn dùng được.',
    DevicesNotFoundError:'Không tìm thấy thiết bị micro. Kiểm tra kết nối micro hoặc dùng tệp âm thanh có sẵn.',
    NotReadableError:'Không đọc được micro. Micro có thể đang được ứng dụng khác sử dụng hoặc bị Windows chặn. Đóng ứng dụng đang thu âm, kiểm tra thiết bị và thử lại.',
    TrackStartError:'Không khởi động được micro. Đóng ứng dụng đang dùng micro và kiểm tra thiết bị trong Windows.',
    SecurityError:'Trình duyệt hoặc chính sách máy đang chặn micro. Kiểm tra quyền truy cập của trang; có thể dùng mẫu nam/nữ mà không cần micro.',
    AbortError:'Việc mở micro bị gián đoạn. Kiểm tra thiết bị và thử lại.',
    NotSupportedError:'Trình duyệt không hỗ trợ định dạng thu âm này. Thử Chrome/Edge mới hoặc nhập tệp WAV/MP3.'
  };
  return messages[error?.name] || 'Không khởi động được bộ thu âm ('+(error?.name||'lỗi không xác định')+'). Thử Chrome/Edge mới hoặc dùng Nhập âm thanh. Hai mẫu nam/nữ không cần micro.';
}
$('skipMicrophone').onclick=()=>{
  microphoneAttempt++;
  if(recorder?.state==='recording')recorder.stop();
  stream?.getTracks().forEach(track=>track.stop());stream=null;recorder=null;
  $('record').disabled=false;$('record').textContent='● Thu mẫu mới (tùy chọn)';$('audioFile').disabled=false;
  microphoneMessage('Đã bỏ qua micro. Chọn giọng nam/nữ có sẵn hoặc nhập tệp âm thanh. Không cần thu lại mẫu.');
};
$('record').onclick=async()=>{
  if(recorder?.state==='recording'){
    $('record').disabled=true;$('record').textContent='Đang hoàn tất bản thu…';recorder.stop();return;
  }
  if(!window.isSecureContext){microphoneMessage(microphoneError());return;}
  if(!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder){microphoneMessage('Trình duyệt chưa hỗ trợ thu micro. Dùng Chrome/Edge mới hoặc nhập tệp âm thanh; hai mẫu nam/nữ không cần micro.');return;}
  const attempt=++microphoneAttempt;
  let capture=null, localRecorder=null, timer=null, promptTimer=null, failed=false;
  const release=()=>{clearTimeout(timer);clearTimeout(promptTimer);capture?.getTracks().forEach(track=>track.stop());if(stream===capture)stream=null;if(recorder===localRecorder)recorder=null;};
  const ready=()=>{if(attempt===microphoneAttempt){$('record').disabled=false;$('record').textContent='● Thu mẫu mới (tùy chọn)';$('audioFile').disabled=false;}};
  $('record').disabled=true;$('audioFile').disabled=true;$('record').textContent='Đang chờ quyền micro…';
  microphoneMessage('Chọn Cho phép trong hộp thoại micro của trình duyệt. Nếu chỉ dùng mẫu nam/nữ, bấm Không dùng micro.');
  promptTimer=setTimeout(()=>{if(attempt===microphoneAttempt)microphoneMessage('Trình duyệt chưa trả lời yêu cầu micro. Kiểm tra hộp thoại quyền ở thanh địa chỉ hoặc bấm Không dùng micro để tiếp tục với mẫu có sẵn.');},15000);
  try{
    capture=await navigator.mediaDevices.getUserMedia({audio:true});clearTimeout(promptTimer);
    if(attempt!==microphoneAttempt){release();return;}
    stream=capture;const chunks=[];let bytes=0;
    const mime=['audio/webm;codecs=opus','audio/webm','audio/mp4'].find(type=>MediaRecorder.isTypeSupported?.(type));
    localRecorder=mime?new MediaRecorder(capture,{mimeType:mime}):new MediaRecorder(capture);recorder=localRecorder;
    localRecorder.ondataavailable=e=>{if(e.data.size){chunks.push(e.data);bytes+=e.data.size;if(bytes>=45*1024*1024 && localRecorder.state==='recording')localRecorder.stop();}};
    localRecorder.onstop=async()=>{
      release();if(attempt!==microphoneAttempt || failed)return;
      $('record').disabled=true;microphoneMessage('Đang giải mã bản thu…');
      try{
        if(!bytes)throw Error('empty');
        await loadAudio(new Blob(chunks,{type:localRecorder.mimeType}));
        if(attempt===microphoneAttempt){$('audio').open=true;microphoneMessage('Đã thu xong. Nghe kiểm tra và tải WAV trong Biên tập âm thanh.');}
      }catch{if(attempt===microphoneAttempt)microphoneMessage('Không giải mã được bản thu. Thử thu lại bằng Chrome/Edge hoặc nhập tệp WAV.');}
      finally{ready();}
    };
    localRecorder.onerror=e=>{failed=true;release();ready();if(attempt===microphoneAttempt)microphoneMessage(microphoneError(e.error));};
    localRecorder.start(1000);
    timer=setTimeout(()=>{if(localRecorder.state==='recording')localRecorder.stop();},10*60*1000);
    $('record').disabled=false;$('record').textContent='■ Dừng thu micro';
    microphoneMessage('Đang thu micro… Bấm Dừng thu micro để hoàn tất. Tự dừng sau 10 phút hoặc khi gần 50 MB.');
  }catch(error){release();ready();if(attempt===microphoneAttempt)microphoneMessage(microphoneError(error));}
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
let activeJob=null;
const readingStyles={neutral:'Tự nhiên: nhịp đọc thông thường.',review:'Review: gần gũi, nhấn ý chính và tên sản phẩm.',storytelling:'Kể chuyện: ngắt nhịp theo diễn biến, biểu cảm theo nội dung.',advertising:'Quảng cáo: rõ thông điệp, năng lượng và nhấn lời kêu gọi.',news:'Tin tức: mạch lạc, phát âm rõ, nhịp ổn định.',meditation:'Thư giãn: chậm và nhẹ, nhiều khoảng nghỉ.',warm:'Ấm áp: nhẹ nhàng, gần gũi.',cheerful:'Vui vẻ: tươi sáng, nhiều năng lượng.',sad:'Buồn: trầm và chậm.'};
function formatDuration(seconds){const total=Math.max(0,Math.floor(Number(seconds)||0)),hours=Math.floor(total/3600),minutes=Math.floor(total%3600/60),rest=total%60;return hours?`${hours}:${String(minutes).padStart(2,'0')}:${String(rest).padStart(2,'0')}`:`${minutes}:${String(rest).padStart(2,'0')}`;}
function renderGeneration(state=generationState){
  generationState=state;
  $('generationPanel').hidden=!state;
  if(!state){$('generate').textContent='▶ Tạo voice';return;}
  if(state.runtime && typeof state.runtime==='object' && serviceStatus){serviceStatus.cosy={...serviceStatus.cosy,...state.runtime};renderComputeStatus();updateProcessingOptions();}
  const completed=state.status==='completed';
  const progress=completed?100:Math.min(99,Math.max(0,Number.isFinite(state.progress)?Math.floor(state.progress):0));
  $('generationProgress').value=progress;$('generationPercent').textContent=progress+'%';
  const phases={queued:'Đang chờ',starting:'Đang khởi động',loading:'Đang nạp mô hình',loading_model:'Đang nạp mô hình',preparing_reference:'Đang chuẩn bị giọng mẫu',synthesizing:'Đang tạo lời đọc',assembling:'Đang ghép âm thanh',cleanup:'Đang lọc ồn / hoàn thiện âm thanh',completed:'Đã tạo xong',cancelled:'Đã dừng',failed:'Tạo voice chưa thành công'};
  const details=[state.message||phases[state.phase]||phases[state.status]||'Đang tạo voice'];
  if(Number.isFinite(state.total_units) && state.total_units>0)details.push(`${Math.max(0,Number(state.completed_units)||0).toLocaleString('vi')}/${state.total_units.toLocaleString('vi')} đoạn`);
  if(Number.isFinite(state.generated_seconds))details.push('Đã tạo '+formatDuration(state.generated_seconds)+' âm thanh');
  if(Number.isFinite(state.elapsed_seconds))details.push('Đã chạy '+formatDuration(state.elapsed_seconds));
  $('generationDetail').textContent=details.join(' · ');
  $('generate').textContent=generationBusy?`Đang tạo ${progress}%`:completed?'✓ Đã tạo 100%':'▶ Tạo voice';
}
function busyControls(){
  for(const button of document.querySelectorAll('#cloneList button,#projectList button,#addClone'))button.disabled=generationBusy;
  $('generate').disabled=generationBusy;
  $('stopGenerate').disabled=!activeJob || !generationBusy || stoppingGeneration;
  renderGeneration();
  for(const id of ['text','inputFormat','dialect','voice','emotion','speed','computeMode','cleanup','loadExample','loadSrtExample','projectFile','textFile','referenceVoice','presetTranscript','title','cloneFile','cloneName','cloneTranscript','cloneConsent','save','record','skipMicrophone','audioFile'])$(id).disabled=generationBusy;
  $('useTranscript').disabled=generationBusy||!$('transcript').value.trim();
}
async function requestJSON(url,options){
  const r=await fetch(url,options);let data;
  try{data=await r.json();}catch{throw Error('Máy chủ trả phản hồi không hợp lệ.');}
  if(!r.ok)throw Error(typeof data.detail==='string'?data.detail:'Không thực hiện được yêu cầu.');
  return data;
}
$('generate').onclick=async()=>{
  if(generationBusy)return;
  if(recorder?.state==='recording' || $('record').textContent.includes('Đang')){notify('Dừng thu mẫu hoặc bấm Không dùng micro trước khi tạo voice.');return;}
  const p=snapshot();
  if(!p.text.trim()){notify('Nhập lời đọc trước khi tạo voice.');$('text').focus();return;}
  if(p.text.length>MAX_SCRIPT_CHARACTERS){notify('Kịch bản tối đa 1.000.000 ký tự.');return;}
  if(!p.voice){notify('Chọn một giọng trước khi tạo voice.');return;}
  const builtin=['hmong-white-female','hmong-white-male'].includes(p.voice);
  const custom=p.voice.startsWith('custom-') || (builtin && serviceStatus?.custom_cloning);
  if(builtin && serviceStatus?.custom_cloning && !serviceStatus.local_cloning && !p.reference_text.trim()){notify('Nhập bản chép đúng lời trong mẫu nam/nữ đã chọn trước khi nhân bản.');$('presetTranscript').focus();return;}
  if(serviceStatus && custom && !serviceStatus.custom_cloning){notify('Mẫu giọng đã được lưu, nhưng chưa có bộ máy nhân bản Hmong Trắng. Không thể tạo lời mới từ mẫu khi chưa có mô hình/dịch vụ phù hợp.');return;}
  generationBusy=true;stoppingGeneration=false;generationState={status:'running',phase:'starting',progress:0,message:'Đang gửi kịch bản…'};busyControls();notify('Đang khởi động tạo voice…');
  try{
    const job=await requestJSON('/api/speech/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:p.text,input_format:p.input_format,dialect:p.dialect,voice:p.voice,emotion:p.emotion,speed:p.speed,compute_mode:p.compute_mode,cleanup:p.cleanup,reference_text:p.reference_text})});
    activeJob=job.id;busyControls();
    let state=job;
    while(['queued','starting','running'].includes(state.status)){
      renderGeneration(state);
      notify(stoppingGeneration?'Đang dừng bộ máy tạo voice…':$('generationDetail').textContent+'. Bạn có thể bấm Dừng.');
      await new Promise(resolve=>setTimeout(resolve,400));
      state=await requestJSON('/api/speech/jobs/'+activeJob);
    }
    renderGeneration(state);
    if(state.status==='cancelled'){notify('Đã dừng tạo voice. Bản thu trước được giữ nguyên.');return;}
    if(state.status!=='completed')throw Error(state.message||'Chưa tạo được voice.');
    if(serviceStatus && state.runtime)serviceStatus.cosy={...serviceStatus.cosy,...state.runtime};
    const url='/api/speech/jobs/'+encodeURIComponent(activeJob)+'/audio';
    if(Number.isFinite(state.audio_bytes) && state.audio_bytes<=25*1024*1024){
      const audio=await fetch(url);if(!audio.ok)throw Error('Không tải được voice vừa tạo.');
      await loadAudio(await audio.blob(),{generated:true});
    }else{loadAudioURL(url,state.audio_bytes);}
    $('audio').open=true;$('audio').scrollIntoView({behavior:'smooth',block:'start'});notify('Đã tạo voice. Nghe kiểm tra hoặc tải WAV ở bên dưới.');
  }catch(e){if(generationState?.status!=='completed')renderGeneration({...generationState,status:'failed',phase:'failed',message:e.message});notify(e.message);}finally{activeJob=null;generationBusy=false;stoppingGeneration=false;busyControls();updateCapabilities();}
};
$('stopGenerate').onclick=async()=>{
  if(!activeJob)return;
  const stoppedJob=activeJob;
  stoppingGeneration=true;$('stopGenerate').disabled=true;notify('Đang dừng bộ máy tạo voice…');
  try{const state=await requestJSON('/api/speech/jobs/'+stoppedJob+'/stop',{method:'POST'});if(activeJob!==stoppedJob)return;renderGeneration(state);notify(state.message||'Đang dừng tạo voice…');}catch(e){if(activeJob!==stoppedJob)return;stoppingGeneration=false;notify(e.message);busyControls();}
};
window.addEventListener('beforeunload',()=>stream?.getTracks().forEach(t=>t.stop()));
renderProjects();update();
function updateCapabilities() {
  if(!serviceStatus)return;
  const s=serviceStatus, custom=$('voice').value.startsWith('custom-') || (s.custom_cloning && ['hmong-white-female','hmong-white-male'].includes($('voice').value));
  $('presetTranscriptPanel').hidden=!['hmong-white-female','hmong-white-male'].includes($('voice').value) || Boolean(s.local_cloning);
  // Preserve the user's selections. Unsupported styles are explained, never silently reset.
  for(const option of $('voice').options)option.disabled=false;
  for(const option of $('emotion').options)option.disabled=false;
  const supported=custom?s.clone_styles.includes($('emotion').value):$('emotion').value==='neutral'||s.emotions;
  $('styleDescription').textContent=(readingStyles[$('emotion').value]||'')+(!supported?' Bộ máy hiện tại chưa hỗ trợ kiểu này; cần bộ máy hỗ trợ để tạo đúng cách đọc.':'');
  $('capability').textContent=custom
    ? (s.local_cloning?'Đang dùng CosyVoice Hmong trên máy. Dùng âm sắc mẫu đã chọn, không cần micro hoặc bản chép mẫu. Nghe kiểm tra phát âm và độ giống giọng.':s.custom_cloning?'Đã chọn mẫu giọng riêng. Mẫu và bản chép được dùng khi tạo voice qua bộ máy nhân bản.':'Đã chọn mẫu giọng riêng. '+(s.cosy?.reason||'Chưa có bộ máy nhân bản.'))
    : (['hmong-white-female','hmong-white-male'].includes($('voice').value) && !s.remote_tts?'Đã chọn mẫu nam/nữ của bạn, không cần micro. Chưa có bộ máy nhân bản Hmong Trắng để đọc lời mới.':s.remote_tts?'Đang dùng dịch vụ đọc đã cấu hình.':'Đang dùng giọng gốc cục bộ. '+(!s.local.dependencies?'Chưa cài thư viện AI. ':'')+(!$('dialect').value||!s.local.tts_models[$('dialect').value]?'Chưa có mô hình cho ngôn ngữ đã chọn.':''));
  $('cloneState').textContent=s.local_cloning?'CosyVoice Hmong cục bộ · đã tải mô hình':s.custom_cloning?'Dịch vụ nhân bản đã cấu hình':s.cosy?.reason||'Chạy install_clone_ai.bat để cài bộ máy nhân bản.';
  renderComputeStatus();
  updateProcessingOptions();update();busyControls();
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
  } catch(e) { notify(e.message); } finally { transcriptionBusy=false; $('transcribe').disabled=!canTranscribe(); }
};
$('useTranscript').onclick = () => { const text=$('transcript').value; if(text.length>MAX_SCRIPT_CHARACTERS){notify('Kết quả vượt 1.000.000 ký tự. Chọn đoạn ngắn hơn hoặc xuất TXT.');return;} if($('text').value && !confirm('Thay kịch bản hiện tại bằng kết quả nhận dạng?'))return; $('text').value=text;$('inputFormat').value='text';update();notify('Đã đưa lời nhận dạng vào kịch bản. Kiểm tra từ và dấu trước khi tạo giọng.'); };
$('exportTranscript').onclick = () => download(new Blob([$('transcript').value],{type:'text/plain;charset=utf-8'}),'-nhan-dang.txt');
fetch('/api/status').then(r=>{if(!r.ok)throw Error();return r.json();}).then(s=>{serviceStatus=s;notify(s.message);updateCapabilities();}).catch(()=>notify('Không kết nối được máy chủ. Thu âm và nhập tệp vẫn dùng được.'));

$('loadExample').onclick = async () => { try { if($('text').value && !confirm('Thay lời đang sửa bằng kịch bản Hmong mẫu?'))return; const r=await fetch('/static/example-hmong.txt');if(!r.ok)throw Error('Không tải được kịch bản mẫu.');$('text').value=await r.text();$('inputFormat').value='text';$('dialect').value='mww';update();updateCapabilities();notify('Đã nạp lời Hmong do bạn cung cấp. Lời này không phải bản chép của hai mẫu giọng.'); }catch(e){notify(e.message);} };
$('loadSrtExample').onclick=()=>{if($('text').value && !confirm('Thay lời đang sửa bằng mẫu review SRT?'))return;$('text').value='1\n00:00:00,200 --> 00:00:02,700\nNyob zoo.\n\n2\n00:00:03,000 --> 00:00:09,000\nHnub no peb saib qhov no ua ke.\n';$('inputFormat').value='srt';$('emotion').value='review';$('dialect').value='mww';update();updateCapabilities();notify('Đã nạp mẫu review SRT. Thay lời và mốc giờ theo video của bạn.');};

$('voice').addEventListener('change',()=>{syncPreset();updateCapabilities();});
let clonePreviewURL=null;
$('cloneFile').onchange=()=>{if(clonePreviewURL)URL.revokeObjectURL(clonePreviewURL);const file=$('cloneFile').files[0];$('clonePreview').hidden=!file;if(file){clonePreviewURL=URL.createObjectURL(file);$('clonePreview').src=clonePreviewURL;}};
async function refreshClones(){
  const r=await fetch('/api/clones'); if(!r.ok)throw Error('Không đọc được thư viện mẫu giọng.');
  const data=await r.json(), selected=$('voice').value;
  for(const o of [...$('voice').options])if(o.value.startsWith('custom-'))o.remove();
  $('cloneList').replaceChildren();
  for(const v of data.voices){
    const option=new Option(v.name+' · Mẫu riêng',v.id);$('voice').append(option);
    const row=document.createElement('div');row.className='project';
    const label=document.createElement('span');label.textContent=v.name+' · '+v.duration+' giây';
    const audio=document.createElement('audio');audio.controls=true;audio.preload='none';audio.src=v.reference;
    const use=document.createElement('button');use.textContent='Chọn giọng';use.onclick=()=>{$('voice').value=v.id;updateCapabilities();notify('Đã chọn '+v.name+'. '+$('cloneState').textContent);};
    const del=document.createElement('button');del.textContent='Xóa';del.onclick=async()=>{if(!confirm('Xóa vĩnh viễn mẫu giọng '+v.name+'?'))return;try{const r=await fetch('/api/clones/'+encodeURIComponent(v.id),{method:'DELETE'});if(!r.ok)throw Error('Không xóa được mẫu giọng.');await refreshClones();}catch(e){notify(e.message);}};
    row.append(label,audio,use,del);$('cloneList').append(row);
  }
  if([...$('voice').options].some(o=>o.value===selected))$('voice').value=selected;
  updateCapabilities();
}
$('addClone').onclick=async()=>{
  const file=$('cloneFile').files[0], name=$('cloneName').value.trim(), transcript=$('cloneTranscript').value.trim();
  if(!file||!name||!$('cloneConsent').checked){notify('Chọn mẫu, nhập tên và xác nhận quyền sử dụng.');return;}
  if(file.size>20*1024*1024){notify('Mẫu tối đa 20 MB.');return;}
  $('addClone').disabled=true;notify('Đang kiểm tra và lưu mẫu giọng…');
  try{
    const form=new FormData();form.append('name',name);form.append('transcript',transcript);form.append('consent','true');form.append('file',file);
    const r=await fetch('/api/clones',{method:'POST',body:form});
    const data=await r.json();if(!r.ok)throw Error(typeof data.detail==='string'?data.detail:'Không lưu được mẫu giọng.');
    await refreshClones();$('voice').value=data.id;updateCapabilities();
    $('cloneConsent').checked=false;notify('Đã lưu mẫu '+data.name+'. '+$('cloneState').textContent);
  }catch(e){notify(e.message);}finally{$('addClone').disabled=generationBusy;}
};
refreshClones().catch(e=>notify(e.message));

$('emotion').addEventListener('change',updateCapabilities);

syncPreset();
updateProcessingOptions();
