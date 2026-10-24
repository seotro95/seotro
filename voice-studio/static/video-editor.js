/* Direct video editing: structured cues, no subtitle file entry required. */
let editorLanguage='',editorVideoId=null,editorCues=[],editorCharacters=[],editorSourceCues=[],editorSourceLanguage='',editorDirty=false,editorBusy=false,editorRevision=0,editorProjectReady=Promise.resolve();
const editorBusyReasons=new Set();
const editorTextLimit=200000;
async function openVideoEditor(){
 const id=dubSource?.id||null;if(id===editorVideoId)return;
 editorVideoId=id;editorLanguage='';editorCues=[];editorCharacters=[];editorSourceCues=[];editorSourceLanguage='';editorDirty=false;editorRevision++;
 $('editor-script-panel').hidden=true;$('editor-script-draft').value='';$('direct-editor').hidden=!id;$('editor-cues').replaceChildren();$('editor-caption').textContent='';editorDrawCharacters();
 if(!id){$('editor-video').removeAttribute('src');return;}
 $('editor-video').src='/api/videos/'+id+'/source';$('editor-seek').max=dubSource.duration;$('editor-save-status').textContent='Đang mở dự án…';
 try{const project=await (editorProjectReady=api('/api/videos/'+id+'/editor'));if(editorVideoId!==id)return;
  editorCharacters=(project.characters||[]).map(c=>({...c}));editorCues=editorNormalizeCues(project.cues||[]);editorLanguage=project.language||'';
  editorSourceCues=(project.source_cues?editorNormalizeCues(project.source_cues):editorCues).map(editorSourceCue);editorSourceLanguage=typeof project.source_language==='string'?project.source_language:editorLanguage;
  setCaptionStyle(project.caption_style||{});if(editorCues.length)syncDirectScript();drawEditorCues();
  $('editor-save-status').textContent=editorCues.length?'Đã mở phụ đề và nhân vật lưu trên máy.':(isHmongStudio()?'Nhập SRT Hmong hoặc Thêm câu và mốc thủ công trước khi tạo voice.':'Chọn Tự tạo phụ đề hoặc Thêm câu; không cần nhập tệp.');
 }catch(e){notify(e.message,true);}
}
async function loadDirectCues(cues,language=null,options={}){
 const id=dubSource?.id;await openVideoEditor();await editorProjectReady;
 if(!id||editorVideoId!==id||dubSource?.id!==id)throw Error('Video đã đổi. Chọn lại tác vụ cho video hiện tại.');
 const previous=editorCues;
 if(options.preserveMetadata&&(cues.length!==previous.length||cues.some((cue,i)=>Number(cue.start)!==Number(previous[i].start)||Number(cue.end)!==Number(previous[i].end))))throw Error('Mốc hoặc số câu đã đổi khi dịch. Giữ phụ đề và phân vai hiện tại; kiểm tra lại bản dịch trước khi nhập.');
 editorCues=editorNormalizeCues(cues,options.preserveMetadata?previous:[]);
 if(options.captureSource||!editorSourceCues.length){editorSourceCues=editorCues.map(editorSourceCue);editorSourceLanguage=language||editorLanguage;}
 if(language!==null)editorLanguage=language;markEditorDirty();drawEditorCues();await saveDirectEditor();
}
function updateDirectCaption(){if(typeof paintCaptionStyle==='function')paintCaptionStyle();const time=$('editor-video').currentTime||0;const cue=editorCues.find(c=>time>=Number(c.start)&&time<Number(c.end));$('editor-caption').textContent=cue?.text||'';}
function drawEditorCues(){
 if(typeof workspaceCaptionLanguage==='function')workspaceCaptionLanguage(editorLanguage);editorDrawCharacters();
 const container=$('editor-cues');container.replaceChildren();
 editorCues.forEach((cue,index)=>{
  const row=element('div',undefined,'editor-cue');row.dataset.cueId=cue.id;
  const title=element('button',`▶ Câu ${index+1}`,'text-button');title.type='button';title.onclick=()=>{$('editor-video').currentTime=Number(cue.start);$('editor-seek').value=cue.start;updateDirectCaption();};row.append(title);
  for(const [key,label]of [['start','Bắt đầu (phút:giây)'],['end','Kết thúc (phút:giây)']]){
   const wrap=element('label',label),input=element('input');input.type='text';input.placeholder='01:30.500';input.value=editorClock(cue[key]);input.title='Phút:giây hoặc giờ:phút:giây, ví dụ 01:30.500';input.setAttribute('aria-label',`${label} câu ${index+1}`);
   input.oninput=()=>{cue[key]=editorParseClock(input.value);input.setCustomValidity(Number.isFinite(cue[key])?'':'Dùng phút:giây, ví dụ 01:30.500');markEditorDirty();updateDirectCaption();};wrap.append(input);row.append(wrap);
  }
  if(isHmongStudio()){
   const wrap=element('label','Nhân vật','editor-cue-character'),select=element('select');select.setAttribute('aria-label',`Nhân vật câu ${index+1}`);select.dataset.cueCharacter=cue.id;
   select.append(new Option('Dẫn chuyện · giọng đang chọn',''),...editorCharacters.map(c=>new Option(c.name,c.id)));select.value=cue.character_id||'';
   select.onchange=()=>{cue.character_id=select.value||null;markEditorDirty();};wrap.append(select);row.append(wrap);
  }
  const text=element('textarea');text.value=cue.text;text.maxLength=4000;text.setAttribute('aria-label',`Nội dung câu ${index+1}`);text.oninput=()=>{cue.text=text.value;markEditorDirty();updateDirectCaption();};row.append(text);
  const del=element('button','Xóa câu','text-button');del.onclick=()=>{editorCues.splice(editorCues.indexOf(cue),1);markEditorDirty();drawEditorCues();};row.append(del);container.append(row);
 });editorSetBusy(null);updateDirectCaption();
}
function checkedEditorCues(){
 if(!editorCues.length)throw Error(isHmongStudio()?'Nhập SRT Hmong hoặc thêm ít nhất một câu trước.':'Tự tạo phụ đề hoặc thêm ít nhất một câu trước.');
 if(editorCues.length>10000||editorCues.reduce((sum,c)=>sum+scriptCharacterCount(c.text.trim()),0)>editorTextLimit)throw Error('Phụ đề video hỗ trợ tối đa 10.000 câu, 200.000 ký tự trong 3 giờ. Dùng Tạo voice riêng từ văn bản cho sách dài hơn.');
 let previous=0;return editorCues.map(c=>{
  const cue={id:c.id,start:Number(c.start),end:Number(c.end),text:c.text.trim(),...(c.character_id?{character_id:c.character_id}:{})};
  if(!Number.isFinite(cue.start)||!Number.isFinite(cue.end)||cue.start<previous||cue.start>=cue.end||cue.end>dubSource.duration+.001||!cue.text||scriptCharacterCount(cue.text)>4000)throw Error('Kiểm tra lời và mốc từng câu: không để trống, quá 4.000 ký tự, chồng nhau hoặc vượt video.');previous=cue.end;return cue;
 });
}
function editorProjectData(){return {project_version:2,cues:editorCues.length?checkedEditorCues():[],characters:editorCharacters.map(c=>({...c})),caption_style:readCaptionStyle(),language:editorLanguage,source_cues:editorSourceCues.map(editorSourceCue),source_language:editorSourceLanguage};}
async function saveDirectEditor(){
 if(!editorVideoId)return;if(!editorSourceCues.length&&editorCues.length){editorSourceCues=editorCues.map(editorSourceCue);editorSourceLanguage=editorLanguage;}const id=editorVideoId,project=editorProjectData(),snapshot=JSON.stringify(project);
 await api('/api/videos/'+id+'/editor',{method:'PUT',headers:{'Content-Type':'application/json'},body:snapshot});
 if(editorVideoId===id&&JSON.stringify(editorProjectData())===snapshot){editorDirty=false;$('editor-save-status').textContent=`Đã lưu ${project.cues.length} câu và ${project.characters.length} nhân vật trên máy.`;}
}
$('editor-save').onclick=()=>saveDirectEditor().catch(e=>notify(e.message,true));
$('editor-add').onclick=()=>{try{let start=Number($('editor-video').currentTime||$('editor-seek').value||0);if(start>=dubSource.duration)start=Math.max(0,dubSource.duration-1);let index=editorCues.findIndex(c=>c.start>start);if(index<0)index=editorCues.length;const previous=index?editorCues[index-1]:null;if(previous&&previous.end>start)throw Error('Thời điểm này đã có câu. Sửa câu hiện tại hoặc chọn một khoảng trống.');const end=Math.min(start+3,editorCues[index]?.start??dubSource.duration);if(end<=start)throw Error('Không còn khoảng trống cho câu mới.');editorCues.splice(index,0,{id:editorNewId('cue'),start:Math.round(start*100)/100,end:Math.round(end*100)/100,text:'Nội dung phụ đề'});markEditorDirty();drawEditorCues();}catch(e){notify(e.message,true);}};
$('editor-video').ontimeupdate=()=>{updateDirectCaption();$('editor-seek').value=($('editor-video').currentTime||0).toFixed(2);};$('editor-video').onerror=()=>{$('editor-note').textContent='Trình duyệt chưa phát được codec này. Bạn vẫn dùng mốc giây và nút Hiện khung hình để xem, sửa và xuất video.';};
$('editor-jump').onclick=()=>{const time=Number($('editor-seek').value);if(!dubSource||!Number.isFinite(time)||time<0||time>=dubSource.duration){notify('Chọn thời điểm nằm trong video.',true);return;}if($('editor-video').readyState>0)$('editor-video').currentTime=time;updateDirectCaption();$('logo-frame').click();};
$('editor-recognize').onclick=()=>beginVideoTask('subtitles');
function editorSrt(cues){function stamp(time){const ms=Math.round(time*1000),h=Math.floor(ms/3600000),m=Math.floor(ms/60000)%60,s=Math.floor(ms/1000)%60;return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')},${String(ms%1000).padStart(3,'0')}`;}return cues.map((c,i)=>`${i+1}\n${stamp(c.start)} --> ${stamp(c.end)}\n${c.text}`).join('\n\n');}
$('editor-dub').onclick=async()=>{try{const cues=checkedEditorCues();await saveDirectEditor();$('dub-script').value=editorSrt(cues);$('dub-format').value='srt';$('dub-offset').value=0;$('logo-enabled').checked=$('editor-logo').checked;await submitDub(true);}catch(e){notify(e.message,true);}};
$('editor-render').onclick=async()=>{if(videoTaskId){notify('Dừng tác vụ hiện tại trước.',true);return;}try{const cues=checkedEditorCues();if($('editor-logo').checked&&(!logoRect||logoVideoId!==dubSource.id))throw Error('Hiện khung hình và khoanh vùng logo cho video này trước.');await saveDirectEditor();taskButtons(true);for(const id of ['dub-preview','dub-download','dub-audio','dub-audio-download'])$(id).hidden=true;const task=await api('/api/video-tasks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({video_id:dubSource.id,action:'render',export_resolution:$('editor-resolution').value,export_quality:$('editor-quality').value,caption_style:readCaptionStyle(),cues,logo:null,logos:$('editor-logo').checked?selectedLogoRegions():[]})});videoTaskId=task.id;videoAutoDub=false;await pollVideoTask();}catch(e){taskButtons(false);notify(e.message,true);}};
const originalVideoChoice=$('dub-existing').onchange;$('dub-existing').onchange=async()=>{if(editorDirty&&!confirm('Phụ đề chưa lưu. Bỏ thay đổi và chuyển video?')){$('dub-existing').value=editorVideoId||'';return;}originalVideoChoice();await openVideoEditor();};
window.addEventListener('beforeunload',e=>{if(editorDirty){e.preventDefault();e.returnValue='';}});

$('editor-translate').onclick=async()=>{try{const cues=checkedEditorCues();await saveDirectEditor();$('dub-script').value=editorSrt(cues);$('dub-format').value='srt';$('translate-subtitles').checked=true;await beginVideoTask('subtitles',true);}catch(e){notify(e.message,true);}};

function syncDirectScript(){$('dub-script').value=editorSrt(editorCues);$('dub-format').value='srt';}
function markEditorDirty(){editorDirty=true;editorRevision++;syncDirectScript();$('editor-save-status').textContent='Có thay đổi chưa lưu. Nhấn Lưu hoặc Xuất video để lưu.';}

async function exportDirectText(extension){try{checkedEditorCues();await saveDirectEditor();const response=await fetch(`/api/videos/${editorVideoId}/editor/export.${extension}`);if(!response.ok){const error=await response.json();throw Error(error.detail||'Chưa xuất được phụ đề.');}downloadText(await response.text(),`subtitles-${editorVideoId.slice(0,8)}.${extension==='timed-txt'?'timed.txt':extension}`);}catch(e){notify(e.message,true);}}
$('editor-export-txt').onclick=()=>exportDirectText('txt');$('editor-export-srt').onclick=()=>exportDirectText('srt');
$('editor-export-video').onclick=async()=>{if(!dubSource){notify('Chọn video trước.',true);return;}if(videoTaskId){notify('Dừng tác vụ hiện tại trước.',true);return;}try{if($('editor-logo').checked&&(!logoRect||logoVideoId!==dubSource.id))throw Error('Khoanh vùng logo cho video này trước.');taskButtons(true);for(const id of ['dub-preview','dub-download','dub-audio','dub-audio-download'])$(id).hidden=true;const task=await api('/api/video-tasks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({video_id:dubSource.id,action:'export',export_resolution:$('editor-resolution').value,export_quality:$('editor-quality').value,logo:null,logos:$('editor-logo').checked?selectedLogoRegions():[]})});videoTaskId=task.id;videoAutoDub=false;await pollVideoTask();}catch(e){taskButtons(false);notify(e.message,true);}};

let editorDraftBase='';
$('editor-script-open').onclick=()=>{try{const cues=checkedEditorCues();editorDraftBase=JSON.stringify(cues);$('editor-script-draft').value=cues.map(c=>c.text.replace(/\n+/g,' ')).join('\n\n');$('editor-script-status').textContent=`${cues.length} đoạn · sửa lời, giữ số đoạn và mốc câu.`;$('editor-script-panel').hidden=false;}catch(e){notify(e.message,true);}};
$('editor-script-close').onclick=()=>{$('editor-script-panel').hidden=true;};
$('editor-script-apply').onclick=async()=>{try{const cues=checkedEditorCues();if(JSON.stringify(cues)!==editorDraftBase)throw Error('Phụ đề đã thay đổi. Đóng bản nháp và mở lại để lấy lời mới nhất.');const paragraphs=$('editor-script-draft').value.trim().split(/\r?\n\s*\r?\n/).map(t=>t.trim());if(paragraphs.length!==cues.length||paragraphs.some(t=>!t||t.length>4000))throw Error(`Cần đúng ${cues.length} đoạn, mỗi đoạn 1–4.000 ký tự. Thêm/xóa câu trong danh sách để chỉnh mốc.`);editorCues=cues.map((c,i)=>({...c,text:paragraphs[i]}));markEditorDirty();drawEditorCues();editorDraftBase=JSON.stringify(checkedEditorCues());await saveDirectEditor();$('editor-script-status').textContent='Đã lưu kịch bản mới; mốc thời gian được giữ. Có thể xuất TXT/SRT hoặc lồng tiếng.';}catch(e){$('editor-script-status').textContent=e.message;notify(e.message,true);}};

function editorClock(seconds){const ms=Math.round(Number(seconds)*1000);return `${String(Math.floor(ms/60000)).padStart(2,'0')}:${String(Math.floor(ms/1000)%60).padStart(2,'0')}.${String(ms%1000).padStart(3,'0')}`;}
function editorParseClock(value){const text=value.trim().replace(',','.');if(/^\d+(?:\.\d{1,3})?$/.test(text))return Number(text);const parts=text.split(':');if(parts.length<2||parts.length>3||!parts.slice(0,-1).every(p=>/^\d+$/.test(p))||!/^\d{1,2}(?:\.\d{1,3})?$/.test(parts.at(-1)))return NaN;const numbers=parts.map(Number);if(numbers.at(-1)>=60||(parts.length===3&&numbers[1]>=60))return NaN;return numbers.reduce((total,n)=>total*60+n,0);}
$('editor-export-timed-txt').onclick=()=>exportDirectText('timed-txt');

// Character names and assignments remain project metadata, never spoken text.
function editorNewId(prefix){return prefix+'-'+(globalThis.crypto?.randomUUID?.()||Date.now().toString(36)+'-'+Math.random().toString(36).slice(2));}
function editorSourceCue(c){return {id:c.id,start:Number(c.start),end:Number(c.end),text:c.text,...(c.character_id?{character_id:c.character_id}:{})};}
function editorNormalizeCues(cues,previous=[]){
 const used=new Set();
 return cues.map((cue,index)=>{
  const old=previous[index],result={...cue};
  if(old){result.id=old.id;result.character_id=old.character_id||null;}
  if(!/^[A-Za-z0-9_-]{1,64}$/.test(result.id||'')||used.has(result.id))result.id=editorNewId('cue');
  used.add(result.id);return result;
 });
}
function editorCharacterVoices(){const engine=voices.find(v=>v.id===$('dub-voice').value)?.engine||config?.hmong_engine;return voices.filter(v=>v.languages?.includes('mww')&&['hmong_native','f5_hmong'].includes(v.engine)&&v.engine===engine&&(v.id==='hmong-male'||v.id==='hmong-female'||v.category==='cloned'));}
function editorCharacterSpeech(cues=null){
 if(!isHmongStudio()||!editorVideoId)return {};
 if(editorVideoId!==dubSource?.id)throw Error('Chọn lại video và phụ đề trước khi tạo voice.');
 if(editorCharacters.length>32)throw Error('Dự án hỗ trợ tối đa 32 nhân vật.');
 cues=cues||checkedEditorCues();const character_voices=Object.create(null),cue_characters=cues.map(c=>c.character_id||null);
 if(cue_characters.some(Boolean)&&$('dub-language').value!=='mww')throw Error('Phân vai nhân vật cần giọng đọc Hmong Trắng.');
 for(const id of new Set(cue_characters.filter(Boolean))){
  const character=editorCharacters.find(c=>c.id===id),voice=editorCharacterVoices().find(v=>v.id===character?.voice_id);
  if(!character||!voice)throw Error('Chọn lại giọng Hmong cho nhân vật '+(character?.name||id)+'. Giọng đã lưu có thể đã bị xóa.');
  if(voice.ready===false)throw Error('Giọng của '+character.name+' chưa sẵn sàng. Tải model hoặc chọn giọng khác trước.');
  character_voices[id]=voice.id;
 }
 return {character_voices,cue_characters};
}
function editorSetBusy(busy,owner='task'){
 if(busy!==null){if(busy)editorBusyReasons.add(owner);else editorBusyReasons.delete(owner);}editorBusy=editorBusyReasons.size>0;
 for(const node of document.querySelectorAll('#editor-cues input,#editor-cues textarea,#editor-cues select,#editor-cues button:last-child,#editor-characters input,#editor-characters select,#editor-characters button'))node.disabled=editorBusy;
 for(const id of ['editor-add','editor-script-open','editor-script-apply','editor-script-draft','workspace-caption-language'])if($(id))$(id).disabled=editorBusy;
}
function editorDrawCharacters(){
 if(!isHmongStudio()){if($('editor-characters'))$('editor-characters').hidden=true;return;}
 let panel=$('editor-characters');
 if(!panel){
  panel=element('section',undefined,'editor-characters');panel.id='editor-characters';
  panel.append(element('h3','Nhân vật và giọng lồng tiếng'),element('p','Thêm nhân vật, chọn giọng riêng rồi gán nhân vật cho từng câu bên dưới. Câu Dẫn chuyện dùng giọng đang chọn ở mục 2.','form-note'));
  const list=element('div');list.id='editor-character-list';panel.append(list);
  const actions=element('div',undefined,'workspace-actions');
  const add=element('button','+ Thêm nhân vật','secondary-button');add.id='editor-character-add';add.type='button';add.onclick=()=>{
   if(editorCharacters.length>=32){notify('Tối đa 32 nhân vật trong một dự án.',true);return;}
   const available=editorCharacterVoices(),voice=available.find(v=>v.id===$('dub-voice').value)||available[0];
   if(!voice){notify('Thêm giọng Hmong Nam, Nữ hoặc giọng cá nhân trước.',true);return;}
   editorCharacters.push({id:editorNewId('character'),name:'Nhân vật '+(editorCharacters.length+1),voice_id:voice.id});markEditorDirty();drawEditorCues();
   $('editor-character-list').lastElementChild?.querySelector('input')?.focus();
  };
  const sort=element('button','Sắp xếp theo mốc','secondary-button');sort.id='editor-cues-sort';sort.type='button';sort.onclick=()=>{editorCues.sort((a,b)=>Number(a.start)-Number(b.start));markEditorDirty();drawEditorCues();};
  const open=element('button','Nhập SRT / dự án JSON','secondary-button');open.id='editor-project-import';open.type='button';open.onclick=()=>$('editor-project-file').click();
  const file=element('input');file.id='editor-project-file';file.type='file';file.accept='.srt,.json,application/json,text/plain';file.hidden=true;file.onchange=async()=>{const selected=file.files[0];file.value='';if(selected)await editorImportFile(selected);};
  const download=element('button','Xuất dự án JSON','secondary-button');download.id='editor-project-export';download.type='button';download.onclick=async()=>{try{await saveDirectEditor();downloadText(JSON.stringify(editorProjectData(),null,2),'voice-studio-project.json');}catch(e){notify(e.message,true);}};
  actions.append(add,sort,open,file,download);panel.append(actions);$('editor-cues').before(panel);
 }
 panel.hidden=false;const list=$('editor-character-list');list.replaceChildren();
 for(const character of editorCharacters){
  const row=element('div',undefined,'editor-character');row.dataset.characterId=character.id;
  const nameLabel=element('label','Tên nhân vật'),name=element('input');name.value=character.name;name.maxLength=80;name.setAttribute('aria-label','Tên nhân vật '+character.name);
  name.oninput=()=>{character.name=name.value;markEditorDirty();editorRefreshCharacterLabels();};name.onblur=()=>{character.name=name.value.trim()||'Nhân vật';name.value=character.name;editorRefreshCharacterLabels();};nameLabel.append(name);
  const voiceLabel=element('label','Giọng riêng'),select=element('select');select.setAttribute('aria-label','Giọng nhân vật '+character.name);select.dataset.characterVoice=character.id;
  const available=editorCharacterVoices();select.append(...available.map(v=>new Option(v.name+(v.category==='cloned'?' · Cá nhân':'')+(v.ready===false?' · Chưa sẵn sàng':''),v.id)));
  if(!available.some(v=>v.id===character.voice_id))select.add(new Option('Giọng đã lưu không còn: '+character.voice_id,character.voice_id));
  select.value=character.voice_id;select.onchange=()=>{character.voice_id=select.value;markEditorDirty();};voiceLabel.append(select);
  const remove=element('button','Xóa nhân vật','text-button');remove.type='button';remove.onclick=()=>{editorCharacters=editorCharacters.filter(c=>c.id!==character.id);for(const cue of [...editorCues,...editorSourceCues])if(cue.character_id===character.id)delete cue.character_id;markEditorDirty();drawEditorCues();};
  row.append(nameLabel,voiceLabel,remove);list.append(row);
 }
 if(!editorCharacters.length)list.append(element('p','Chưa có nhân vật riêng. Các câu dùng giọng Dẫn chuyện.','form-note'));
 editorSetBusy(null);
}
function editorRefreshCharacterLabels(){
 for(const select of document.querySelectorAll('[data-cue-character]'))for(const option of select.options){const character=editorCharacters.find(c=>c.id===option.value);if(character)option.textContent=character.name||'Nhân vật';}
}
function editorParseSrt(text){
 const stamp=value=>{const m=value.match(/^(\d{1,3}):(\d{2}):(\d{2})[,.](\d{3})$/);if(!m||Number(m[2])>=60||Number(m[3])>=60)throw Error('Mốc SRT không hợp lệ. Dùng giờ:phút:giây,mili giây.');return Number(m[1])*3600+Number(m[2])*60+Number(m[3])+Number(m[4])/1000;};
 return text.replace(/^\uFEFF/,'').replace(/\r/g,'').trim().split(/\n\s*\n/).map(block=>{
  const lines=block.split('\n');if(/^\d+$/.test(lines[0].trim()))lines.shift();const times=(lines.shift()||'').trim().match(/^(\S+)\s+-->\s+(\S+)$/);
  if(!times||!lines.join('\n').trim())throw Error('SRT cần mốc bắt đầu/kết thúc và lời cho mỗi câu.');return {start:stamp(times[1]),end:stamp(times[2]),text:lines.join('\n').trim()};
 });
}
function editorCheckedImport(project){
 if(!project||!Array.isArray(project.cues)||![1,2].includes(project.project_version??1))throw Error('Dự án JSON không hợp lệ hoặc thuộc phiên bản mới hơn.');
 const characters=project.characters||[];if(!Array.isArray(characters)||characters.length>32)throw Error('Dự án hỗ trợ tối đa 32 nhân vật.');
 const ids=new Set();for(const c of characters){if(!/^[A-Za-z0-9_-]{1,64}$/.test(c.id||'')||ids.has(c.id)||typeof c.name!=='string'||!c.name.trim()||c.name.length>80||typeof c.voice_id!=='string'||!c.voice_id)throw Error('Kiểm tra tên, mã và giọng của các nhân vật trong dự án.');ids.add(c.id);}
 const validate=cues=>{let previous=0;if(!Array.isArray(cues)||cues.length>10000)throw Error('Dự án có quá nhiều câu.');for(const cue of cues){if(typeof cue.text!=='string'||!cue.text.trim()||scriptCharacterCount(cue.text)>4000||!Number.isFinite(cue.start)||!Number.isFinite(cue.end)||cue.start<previous||cue.end<=cue.start||cue.end>dubSource.duration+.001)throw Error('Mốc hoặc lời trong dự án không hợp lệ cho video này.');if(cue.character_id&&!ids.has(cue.character_id))throw Error('Câu đang tham chiếu nhân vật không có trong dự án.');previous=cue.end;}if(cues.reduce((sum,c)=>sum+scriptCharacterCount(c.text.trim()),0)>editorTextLimit)throw Error('Phụ đề video tối đa 200.000 ký tự trong 3 giờ. Dùng Tạo voice riêng từ văn bản cho sách dài hơn.');return editorNormalizeCues(cues);};
 const cues=validate(project.cues),source=(project.source_cues?validate(project.source_cues):cues).map(editorSourceCue);
 return {cues,characters:characters.map(c=>({id:c.id,name:c.name.trim(),voice_id:c.voice_id})),source,language:typeof project.language==='string'?project.language:'',sourceLanguage:typeof project.source_language==='string'?project.source_language:project.language||'',style:project.caption_style||{}};
}
async function editorImportFile(file){
 try{
  if(editorBusy)throw Error('Đợi hoặc dừng tác vụ trước khi nhập dự án.');if(!dubSource)throw Error('Chọn video trước.');
  const videoId=editorVideoId,revision=editorRevision;
  if(file.size>editorTextLimit*8+1000000)throw Error('Tệp quá lớn. Phụ đề video hỗ trợ 200.000 ký tự trong 3 giờ.');
  const text=(await file.text()).replace(/^\uFEFF/,'');
  if(editorBusy||editorVideoId!==videoId||dubSource?.id!==videoId||editorRevision!==revision)throw Error('Video hoặc dự án đã đổi khi đọc tệp. Nhập lại tệp cho bản đang mở.');
  let imported;
  if(file.name.toLowerCase().endsWith('.json'))imported=editorCheckedImport(JSON.parse(text));
  else{
   const cues=editorParseSrt(text),keys=new Map();for(const c of editorCues){const key=JSON.stringify([c.start,c.end,c.text]);keys.set(key,keys.has(key)?null:c);}
   for(const cue of cues){const old=keys.get(JSON.stringify([cue.start,cue.end,cue.text]));if(old){cue.id=old.id;cue.character_id=old.character_id;}}
   imported=editorCheckedImport({project_version:2,cues,characters:editorCharacters,language:editorLanguage,caption_style:readCaptionStyle()});
  }
  editorCues=imported.cues;editorCharacters=imported.characters;editorSourceCues=imported.source;editorSourceLanguage=imported.sourceLanguage;editorLanguage=imported.language;
  setCaptionStyle(imported.style);markEditorDirty();drawEditorCues();await saveDirectEditor();notify('Đã nhập '+editorCues.length+' câu; tên nhân vật chỉ lưu trong dự án, không đọc thành lời.');
 }catch(e){notify(e.message,true);}
}
const editorOriginalTaskButtons=taskButtons;taskButtons=function(busy){editorOriginalTaskButtons(busy);editorSetBusy(busy);};
const editorOriginalRefreshVoices=refreshVoices;refreshVoices=async function(){await editorOriginalRefreshVoices();editorDrawCharacters();};
for(const id of ['editor-dub','editor-render','editor-translate']){
 const action=$(id).onclick;$(id).onclick=async function(...args){
  if(editorBusy){notify('Đợi hoặc dừng tác vụ hiện tại trước.',true);return;}
  editorSetBusy(true,id);try{return await action.apply(this,args);}finally{editorSetBusy(false,id);}
 };
}
