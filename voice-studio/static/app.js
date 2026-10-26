'use strict';
const $ = (id) => document.getElementById(id);
let config, voices = [], currentTab = 'create', polling = false, activeOutputId = null;
let studioBootstrapPromise=null,studioReady=false,studioInitialized=false,voiceSubmitting=false,voiceAttempt=0,userNavigated=false;
const generateStatus=document.createElement('p');generateStatus.id='generate-status';generateStatus.className='form-note';generateStatus.setAttribute('role','status');generateStatus.setAttribute('aria-live','polite');$('generate').after(generateStatus);
const studioRetry=document.createElement('button');studioRetry.id='voice-retry-studio';studioRetry.className='secondary-button';studioRetry.textContent='Thử kết nối lại';studioRetry.hidden=true;generateStatus.after(studioRetry);
function voiceFeedback(message,error=false,title){generateStatus.textContent=message;generateStatus.classList.toggle('error-message',error);if(title){$('output-title').textContent=title;$('output-subtitle').textContent=message;}if(error)notify(message,true);}
studioRetry.onclick=async()=>{try{await ensureStudioReady(true);}catch{}};
function isHmongStudio(){return config?.variant==='hmong';}
function scriptCharacterLimit(){const limit=Number(config?.max_characters);return Number.isInteger(limit)&&limit>0?limit:200000;}
function scriptCharacterCount(text){let count=0;for(const character of text)count++;return count;}
function updateScriptLimits(){
 const limit=scriptCharacterLimit(),label=limit.toLocaleString('vi-VN');
 for(const id of ['script','dub-script','workspace-free-script','writing-result','editor-script-draft'])if($(id))$(id).maxLength=limit;
 for(const [id,text]of [['dub-script','Lời lồng tiếng'],['workspace-free-script','Lời để tạo voice']]){const node=document.querySelector('label[for="'+id+'"]');if(node)node.textContent=text+' · tối đa '+label+' ký tự';}
 if($('longform-note')){$('longform-note').hidden=!isHmongStudio();$('longform-note').textContent='Kịch bản gốc hỗ trợ đến '+label+' ký tự. TXT Hmong trên 20.000 ký tự tự chia thành nhiều phần để đọc hết, không dừng ở mốc 3 giờ; nghe từng phần và tải toàn bộ trong ZIP. SRT và xuất video giữ giới hạn thời lượng riêng.';}
 $('script').oninput();
}
function isNativeHmong(){return isHmongStudio()&&(config?.hmong_backend==='native'||config?.hmong_engine==='hmong_native');}
let hmongVoiceId=null,hmongVoiceSyncing=false;
function updateHmongVoiceChoices(){
 if(!isHmongStudio())return;
 for(const [group,select,status,sample]of [['hmong-voice-choices','voice','hmong-selected-voice','hmong-reference-sample'],['workspace-hmong-voice-choices','dub-voice','workspace-hmong-selected-voice','workspace-hmong-reference-sample']]){
  const voice=voices.find(v=>v.id===$(select).value);
  for(const button of $(group).querySelectorAll('[data-hmong-gender],[data-hmong-voice]')){const id=button.dataset.hmongVoice||'hmong-'+button.dataset.hmongGender;const available=voices.some(v=>v.id===id);if(button.dataset.hmongVoice)button.hidden=!available;button.disabled=!available;const selected=voice?.id===id;button.setAttribute('aria-pressed',String(selected));button.classList.toggle('primary-button',selected);button.classList.toggle('secondary-button',!selected);}
  $(status).textContent=voice?'Đang chọn: '+voice.name+(voice.ready===false?' · Cần tải model':''):'Chưa có giọng phù hợp với bộ lọc.';
  const url=voice?.sample_url||(voice?.category==='cloned'?'/api/voices/'+voice.id+'/sample':'');
  const audio=$(sample);if(audio.getAttribute('src')!==(url||null)){audio.pause();if(url)audio.src=url;else audio.removeAttribute('src');}audio.hidden=!url;audio.previousElementSibling.hidden=!url;
 }
}
function selectHmongVoice(id){
 const voice=voices.find(v=>v.id===id);if(!isHmongStudio()||!voice)return;
 const changed=hmongVoiceId!==id||$('dub-voice').value!==id;hmongVoiceId=id;
 hmongVoiceSyncing=true;
 try{
  for(const [language,source,native]of [['language','voice-source','create-native'],['dub-language','dub-voice-source','workspace-native']]){$(language).value=voice.languages[0];$(source).value='all';$(native).value='all';}
  updateVoiceOptions();updateDubVoices();$('voice').value=id;$('dub-voice').value=id;updateVoice();updateDubVoiceInfo();
 }finally{hmongVoiceSyncing=false;}
 if(changed&&typeof workspaceInvalidate==='function')workspaceInvalidate();
 if(changed&&typeof workspaceFreeVoice!=='undefined'&&workspaceFreeVoice){workspaceFreeVoice=null;$('workspace-free-audio').pause();$('workspace-free-audio').hidden=true;if($('workspace-free-audio')._chapterSelect)$('workspace-free-audio')._chapterSelect.hidden=true;$('workspace-free-status').textContent='Giọng đã đổi. Tạo voice riêng lại để áp dụng giọng mới.';}
}
function adoptFilteredHmongVoice(select){
 if(!isHmongStudio()||!studioInitialized||hmongVoiceSyncing)return;
 const id=$(select).value,voice=voices.find(v=>v.id===id);if(!voice)return;
 const changed=hmongVoiceId!==id;hmongVoiceId=id;
 const main=select==='voice',target=main?'dub-voice':'voice';
 hmongVoiceSyncing=true;
 try{
  if(![...$(target).options].some(option=>option.value===id)){
   $(main?'dub-language':'language').value=voice.languages[0];
   $(main?'dub-voice-source':'voice-source').value='all';
   $(main?'workspace-native':'create-native').value='all';
   if(main)updateDubVoices();else updateVoiceOptions();
  }
  $(target).value=id;updateVoice();updateDubVoiceInfo();
 }finally{hmongVoiceSyncing=false;}
 if(changed&&typeof workspaceInvalidate==='function')workspaceInvalidate();
 if(changed&&typeof workspaceInvalidateFreeVoice==='function')workspaceInvalidateFreeVoice();
}
function selectLibraryVoice(voice){
 if(isHmongStudio()){selectHmongVoice(voice.id);return;}
 $('language').value=voice.languages[0];$('voice-source').value='all';$('create-native').value='all';updateVoiceOptions();$('voice').value=voice.id;updateVoice();
}
function hmongLauncher(){return isNativeHmong()?'MO_VOICE_STUDIO_HMONG.bat':'tools/MO_F5_HMONG.bat';}
function hmongSteps(){const steps=Number($('hmong-steps')?.value||config?.hmong_steps||16);return [4,8,16,32].includes(steps)?steps:16;}
const hmongEmotions=['neutral','warm','joyful','sad','serious','suspense'];
function hmongExpressionSettings(){
 const emotion=$('hmong-emotion')?.value;
 const strength=Number($('hmong-emotion-strength')?.value);
 return {emotion:hmongEmotions.includes(emotion)?emotion:'warm',emotion_strength:Number.isFinite(strength)&&strength>=0&&strength<=1?strength:0.65,auto_rhythm:$('hmong-auto-rhythm')?.checked??false,delivery:$('delivery')?.value||'story',paragraph_pause:Number($('paragraph-pause')?.value||0)};
}
function hmongExpressionChanged(){
 if(typeof workspaceBusy!=='undefined'&&workspaceBusy)return;
 if(typeof workspaceInvalidate==='function')workspaceInvalidate();
 if(typeof workspaceFreeVoice!=='undefined'&&workspaceFreeVoice){workspaceFreeVoice=null;$('workspace-free-audio').pause();$('workspace-free-audio').hidden=true;if($('workspace-free-audio')._chapterSelect)$('workspace-free-audio')._chapterSelect.hidden=true;$('workspace-free-status').textContent='Nhịp đọc hoặc sắc thái đã đổi. Tạo voice riêng lại để áp dụng thiết lập mới.';}
}
function updateHmongPauseLabels(){
 const label=$('hmong-auto-rhythm').checked?'Nghỉ bổ sung giữa câu/đoạn (giây)':'Nghỉ giữa các câu/đoạn (giây)';
 for(const id of ['paragraph-pause','dub-hmong-paragraph-pause'])document.querySelector('label[for="'+id+'"]').textContent=label;
}
function insertHmongScriptControl(emotion){
 const field=$('script'),start=field.selectionStart,end=field.selectionEnd,selected=field.value.slice(start,end);
 const replacement='[emotion='+emotion+'] '+selected+(selected?' [emotion='+hmongExpressionSettings().emotion+'] ':'');
 field.setRangeText(replacement,start,end,'end');field.focus();field.oninput();
}
function setupHmongExpressionControls(){
 const dubSettings=$('dub-hmong-settings');document.querySelector('#panel-dub .workspace-voice-tools').append(dubSettings);
 $('dub-hmong-delivery').replaceChildren(...[...$('delivery').options].map(option=>option.cloneNode(true)));
 const delivery=[...$('delivery').options].some(option=>option.value===config.delivery)?config.delivery:'story';
 const emotion=hmongEmotions.includes(config.emotion)?config.emotion:'warm';
 const configuredStrength=Number(config.emotion_strength??0.65),strength=Number.isFinite(configuredStrength)&&configuredStrength>=0&&configuredStrength<=1?configuredStrength:0.65;
 for(const id of ['delivery','dub-hmong-delivery'])$(id).value=delivery;
 for(const id of ['hmong-emotion','dub-hmong-emotion'])$(id).value=emotion;
 for(const id of ['hmong-emotion-strength','dub-hmong-emotion-strength']){$(id).value=String(strength);$(id+'-value').textContent=Math.round(strength*100)+'%';}
 for(const id of ['hmong-auto-rhythm','dub-hmong-auto-rhythm'])$(id).checked=typeof config.auto_rhythm==='boolean'?config.auto_rhythm:false;
 $('dub-hmong-paragraph-pause').value=$('paragraph-pause').value;
 for(const [left,right]of [['delivery','dub-hmong-delivery'],['hmong-emotion','dub-hmong-emotion'],['hmong-emotion-strength','dub-hmong-emotion-strength'],['hmong-auto-rhythm','dub-hmong-auto-rhythm'],['paragraph-pause','dub-hmong-paragraph-pause']]){
  for(const [source,target]of [[left,right],[right,left]])$(source).addEventListener(source.includes('strength')||source.includes('pause')?'input':'change',()=>{
   if(source.includes('auto-rhythm'))$(target).checked=$(source).checked;else $(target).value=$(source).value;
   if(source.includes('strength'))for(const id of [left,right])$(id+'-value').textContent=Math.round(Number($(id).value)*100)+'%';
   updateHmongPauseLabels();hmongExpressionChanged();
  });
 }
 updateHmongPauseLabels();
 document.querySelectorAll('[data-hmong-emotion]').forEach(button=>button.onclick=()=>insertHmongScriptControl(button.dataset.hmongEmotion));
 $('hmong-insert-example').onclick=()=>{const field=$('script');field.setRangeText('Nyob zoo. **Ua tsaug.** [pause=0.5] [emotion=warm]Ua tsaug rau koj mloog.',field.selectionStart,field.selectionEnd,'end');field.focus();field.oninput();};
}
function updateHmongReferenceNote(){if(isHmongStudio()){ $('hmong-reference-note').textContent=(config.hmong_ready?(isNativeHmong()?'Bộ đọc Hmong nhanh thử nghiệm đã sẵn sàng. Giữ cách phát âm bạn đã xác nhận; tốc độ 30× cần đo thực tế. ':'Mô hình Hmong đã sẵn sàng. Tạo giọng có thể chậm trên CPU; không cam kết 1 giờ voice trong 2 phút. '):(isNativeHmong()?'Lần đầu cần tải và kiểm tra khoảng 580 MB mô hình cho bộ đọc nhanh thử nghiệm. Bấm Tải model hoặc mở MO_VOICE_STUDIO_HMONG.bat. ':'Lần chuẩn bị đầu cần Internet và dung lượng trống để tải/kiểm tra mô hình từ nguồn gốc. Bấm Tải model hoặc làm theo hướng dẫn của gói. '))+(config.hmong_reference_note||'Dùng mẫu tham chiếu Hmong rõ lời. Với giọng cá nhân, cần mẫu 3–8 giây và lời khớp chính xác đoạn thu.'); }}
function hideStudioControl(id){const node=$(id);if(node)node.hidden=true;document.querySelectorAll('label[for="'+id+'"]').forEach(label=>label.hidden=true);}
function applyStudioVariant(){
 if(!isHmongStudio())return;
 $('hmong-help-tools').hidden=false;
 $('create-subtitle-timing').checked=config.subtitle_timing_default!==false;
 for(const selector of ['#workspace-sync-mode option[value="adaptive"]','#workspace-sync-tempo option[value="4"]'])document.querySelector(selector).hidden=false;
 $('workspace-sync-mode').value='adaptive';$('workspace-sync-tempo').value='4';
 document.title=config.app_name||'Voice Studio Hmong';
 const intro=document.querySelector('#panel-create .page-heading > p');if(intro)intro.textContent=isNativeHmong()?'Bộ đọc Hmong nhanh thử nghiệm và chuyển chất giọng theo mẫu của bạn. Cần nghe đánh giá phát âm và độ giống giọng; chưa kiểm chứng 30×.':'Tạo lời đọc Hmong Trắng / Hmoob Daw từ văn bản và mẫu giọng của bạn.';
 const languageFeature=document.querySelector('#panel-create .feature[data-tab="voices"] p');if(languageFeature)languageFeature.textContent='Các mẫu Hmong có sẵn, Ngọc Huyền và các giọng cá nhân đã thêm.';
 const brand=document.querySelector('.brand');if(brand){brand.setAttribute('aria-label',document.title);const name=brand.querySelector(':scope > span:last-child');if(name){name.replaceChildren(document.createTextNode(document.title),element('small','PHÒNG THU TIẾNG HMONG'));}}
 for(const id of ['language','clone-language','writing-language','dub-language']){if([...$(id).options].some(option=>option.value===config.default_language))$(id).value=config.default_language;}
 for(const id of ['quality','nano-parallel','nano-threads','nano-steps','dub-nano-steps','dub-parallel','use-nano','target-preset','create-fast','studio-fast','workspace-processing','asr-language','asr-quality','editor-recognize','auto-subtitles','auto-dub','workspace-all','workspace-system-help','dub-add-system-voice'])hideStudioControl(id);
 const targetNote=$('benchmark-speed')?.nextElementSibling;if(targetNote?.tagName==='P')targetNote.hidden=true;
 const localNote=document.querySelector('#panel-create .local-note');if(localNote)localNote.textContent=isNativeHmong()?'Bộ đọc nhanh tạo lời Hmong rồi chuyển chất giọng theo mẫu nam/nữ của bạn. Không dùng số bước F5. Mô hình được giữ trong RAM cho lượt sau; tốc độ cần đo cả quá trình tạo lời, chuyển giọng và xuất audio. Phát âm, thanh điệu và độ giống giọng vẫn cần nghe đánh giá; chưa kiểm chứng 1 giờ voice / 2 phút. Có GPU NVIDIA: chạy tools/install_hmong_cuda.bat rồi mở lại MO_VOICE_STUDIO_HMONG.bat.':'Mặc định 16 bước, đọc liền cụm và không thêm nghỉ tự động để giảm số lượt tạo. Nhấn giọng áp dụng cho cả cụm để giữ ngữ cảnh; bật nhịp tự động khi cần nghỉ rõ từng câu. 4/8 bước chỉ dùng bản nháp, có thể đọc thiếu hoặc kém rõ. Riêng 4 bước có thể dùng INT8 để tự tăng tốc CPU, tự quay về độ chính xác gốc nếu không phù hợp. Mô hình được giữ trong RAM cho lượt sau. Có GPU NVIDIA: chạy tools/install_hmong_cuda.bat để cài bộ GPU riêng rồi mở lại tool; tốc độ 30× vẫn cần đo thực tế.';
 for(const id of ['hmong-settings','dub-hmong-settings','hmong-asr-note','hmong-script-controls'])$(id).hidden=false;
 for(const id of ['hmong-voice-choices','workspace-hmong-voice-choices']){$(id).hidden=false;$(id).querySelectorAll('[data-hmong-gender],[data-hmong-voice]').forEach(button=>button.onclick=()=>selectHmongVoice(button.dataset.hmongVoice||'hmong-'+button.dataset.hmongGender));}
 updateHmongReferenceNote();updateSubtitleMode();
 for(const id of ['hmong-steps','dub-hmong-steps']){if(isNativeHmong())hideStudioControl(id);else $(id).value=String([4,8,16,32].includes(Number(config.hmong_steps))?Number(config.hmong_steps):16);}
 $('paragraph-pause').value='0';
 setupHmongExpressionControls();
 for(const [id,other]of [['hmong-steps','dub-hmong-steps'],['dub-hmong-steps','hmong-steps']])$(id).onchange=()=>{$(other).value=$(id).value;hmongExpressionChanged();};
 for(const id of ['create-native','workspace-native'])$(id).replaceChildren(new Option('Tất cả giọng','all'),new Option('Hmong','mww'),new Option('Giọng cá nhân','cloned'));
 for(const id of ['voice-source','dub-voice-source'])$(id).replaceChildren(new Option('Tất cả nguồn','all'),new Option('Giọng AI Hmong','ai'));
 const transcript=$('transcript');transcript.required=!isNativeHmong();transcript.placeholder=isNativeHmong()?'Không bắt buộc. Có thể ghi lời mẫu bằng ngôn ngữ gốc; tool lấy chất giọng từ âm thanh để đọc tiếng Hmong.':'Nhập đúng lời Hmong trong đoạn 3–8 giây đang chọn. Hai MP3 đi kèm được điền lời mẫu bạn đã cung cấp sau khi đối chiếu tệp; có thể nghe và sửa nếu cần.';
 const transcriptLabel=document.querySelector('label[for="transcript"]');if(transcriptLabel)transcriptLabel.textContent=isNativeHmong()?'Lời trong mẫu · ngôn ngữ bất kỳ (không bắt buộc)':'Kiểm tra / sửa lời Hmong cho khớp đoạn mẫu 3–8 giây (bắt buộc)';
 const cloneLanguageLabel=document.querySelector('label[for="clone-language"]');if(cloneLanguageLabel)cloneLanguageLabel.textContent='Ngôn ngữ lời đọc đầu ra';
 if(isNativeHmong()){$('clone-language').replaceChildren(new Option('Hmong Trắng · mẫu thu có thể nói ngôn ngữ bất kỳ','mww'));const clipNote=$('clone-reference').querySelector('p:last-child');if(clipNote)clipNote.textContent='Chọn một người nói rõ tiếng. Mẫu có thể là tiếng Hmong hoặc ngôn ngữ khác; không cần nhập lời mẫu. Lời mới vẫn nhập bằng chữ Hmong RPA.';}
 const sampleNote=document.querySelector('label[for="clone-file"] small');if(sampleNote)sampleNote.textContent='Tệp 3–30 giây · chọn đoạn 3–8 giây bên dưới · WAV/MP3/M4A/FLAC/OGG/WEBM · tối đa 20 MB';
 const cloneLength=document.querySelector('#panel-clone .clone-intro p');if(cloneLength)cloneLength.textContent=isNativeHmong()?'Tải mẫu nói ngôn ngữ bất kỳ → chọn đoạn → lưu và tạo thử tiếng Hmong':'Tải mẫu → chọn đoạn và lời → lưu hoặc tạo thử giọng';
 const cloneIntro=document.querySelector('#panel-clone .page-heading p');if(cloneIntro)cloneIntro.textContent=isNativeHmong()?'Tải giọng từ bên ngoài, kể cả người không nói tiếng Hmong. Tool lấy chất giọng từ đoạn thu 3–8 giây rồi đọc văn bản Hmong. Hai mẫu đi kèm dùng lời do bạn cung cấp và xác nhận khớp đoạn thu. Độ giống giọng phụ thuộc bản thu và mô hình; hãy tạo thử để nghe so sánh.':'Có thể tải hai MP3 nam/nữ đi kèm. Tool đối chiếu tệp bằng SHA256 rồi điền lời mẫu. Với hai mẫu đi kèm, lời do bạn cung cấp và xác nhận khớp đoạn thu. Bạn vẫn có thể nghe và sửa; mẫu khác cần lời khớp đoạn 3–8 giây đang chọn.';
 $('clone-reference').hidden=false;$('clone-save-test').hidden=false;
 $('clone-submit').textContent='◎ Lưu hồ sơ giọng';
 const cloneNote=$('clone-form').lastElementChild;if(cloneNote)cloneNote.textContent='Lưu hồ sơ chỉ chuẩn bị mẫu tham chiếu. Chọn “Lưu và tạo thử giọng Hmong” để tạo một bản thu thật và theo dõi tiến độ ở Tạo giọng. Có thể tải WAV/MP3 sau khi tạo xong.';
 const help=$('help-dialog');help.querySelector('h2').textContent='Phòng thu giọng Hmong cục bộ';const helpList=help.querySelector('ol');helpList.replaceChildren(...['Lần chuẩn bị đầu cần Internet để tải và kiểm tra mô hình Hmong từ nguồn gốc; không dùng bộ tải giọng Việt/Anh.', isNativeHmong()?'Giọng cá nhân dùng mẫu thu 3–8 giây bằng ngôn ngữ bất kỳ, không bắt buộc lời mẫu. Chọn hồ sơ vừa lưu để đọc văn bản Hmong RPA.':'Giọng cá nhân cần mẫu Hmong 3–8 giây và lời khớp chính xác mẫu. Nhập chữ Hmong RPA, giữ đủ chữ đuôi ghi thanh điệu.', isNativeHmong()?'Bộ đọc nhanh đang thử nghiệm, tạo lời Hmong rồi chuyển chất giọng theo mẫu. Không có số bước F5; cần nghe kiểm tra phát âm, thanh điệu và độ giống giọng. Chưa kiểm chứng 30×.':'Dùng 16 bước mặc định hoặc 32 bước để tăng chất lượng. 4/8 bước là bản nháp, có thể kém rõ. Riêng 4 bước tự thử INT8 trên CPU nếu phù hợp; 16/32 bước giữ độ chính xác gốc. Nghe kiểm tra trước khi sử dụng.', 'Sắc thái thay đổi nhịp, cường độ và khoảng nghỉ, không phải cảm xúc được huấn luyện trong mô hình. Không đổi cao độ để tránh ảnh hưởng thanh điệu Hmong. Nhịp tự động có thể tạo lâu hơn; tắt để ưu tiên tốc độ.'].map(text=>element('li',text)));const helpNotes=help.querySelectorAll(':scope > p');if(helpNotes[0])helpNotes[0].textContent='Tool lưu từng đoạn để có thể dừng và tiếp tục. Suy luận Hmong có thể chậm trên CPU; giới hạn thời lượng âm thanh không phải cam kết thời gian xử lý.';if(helpNotes[1])helpNotes[1].textContent=config.hmong_reference_note||'Chất lượng Hmong và độ giống giọng phụ thuộc mô hình, bản thu và lời tham chiếu; cần nghe đánh giá.';if(helpNotes[2])helpNotes[2].textContent='Chưa có nhận dạng Hmong từ video. Nhập hoặc sửa TXT/SRT thủ công. Các thẻ **nhấn**, [pause=0.5] và [emotion=warm] được xử lý trước khi tạo giọng, không được đọc thành lời.';
 $('benchmark-speed').textContent='◷ Đo tốc độ và thử 6 từ Hmong';
 $('workspace-status').textContent='Nhập phụ đề SRT Hmong hoặc thêm lời và mốc thủ công, rồi chọn giọng để tạo voice.';
 $('subtitle-health').textContent='Chưa hỗ trợ nhận dạng Hmong từ video. Bạn vẫn có thể nhập/sửa TXT/SRT và xuất video có voice/phụ đề.';
}

const hmongPronunciationSample='Peb ua hauj lwm. Thaj chaw no zoo nkauj. Nyob qab roob. Peb faib mov. Kuv rov los tsev. Nws hnav ris.';
const samples = {mww:'Nyob zoo, kuv zoo siab tau ntsib koj. Hnub no peb yuav mloog ib zaj dab neeg. Ua tsaug rau koj mloog.',vi:'Có những câu chuyện bắt đầu bằng một lời chào. Có những ý tưởng chỉ cần một giọng nói để chạm đến trái tim. Chào mừng bạn đến với Voice Studio — nơi câu chữ của bạn cất thành lời.', 'en-US':'Every great story begins with a voice. Welcome to your personal studio, where a little imagination becomes something worth listening to.', 'en-GB':'Every great story begins with a voice. Welcome to your personal studio, where a little imagination becomes something worth listening to.', ja:'こんにちは。あなたの物語を、あなたらしい声で届けましょう。', ko:'안녕하세요. 당신만의 목소리로 새로운 이야기를 시작해 보세요.'};
function notify(message, error = false) { const el = $('notice'); el.textContent = message; el.classList.toggle('error', error); el.hidden = !message; }
async function api(path, options = {}) { if(isHmongStudio()&&path==='/api/speech'&&typeof options.body==='string'){const payload=JSON.parse(options.body);Object.assign(payload,hmongExpressionSettings());if(payload.subtitle_timing!==false&&(payload.input_format==='srt'||hasScriptTimeRanges(payload.text||''))){payload.input_format='srt';payload.cue_fit??='adaptive';if(payload.cue_fit==='adaptive')payload.max_cue_tempo??=4;}if(isNativeHmong())delete payload.hmong_steps;else payload.hmong_steps=hmongSteps();options={...options,body:JSON.stringify(payload)};} let res;try{res=await fetch(path,options);}catch(e){throw new Error('Mất kết nối với tool. Giữ cửa sổ CMD mở; nếu đã tắt, chạy lại '+(isHmongStudio()?hmongLauncher():'MO_VOICE_STUDIO.bat')+' và dùng tab vừa mở.');} if(!res.ok){let failure;try{failure=await res.json();}catch{}const error=new Error(typeof failure?.detail==='string'?failure.detail:`Yêu cầu không thành công (${res.status}). Kiểm tra dữ liệu và thử lại.`);error.status=res.status;error.field=failure?.field;error.code=failure?.code;error.unsupportedCharacters=failure?.unsupported_characters;error.errors=failure?.errors;throw error;} return res.status === 204 ? null : res.json(); }
function element(tag, text, cls) { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (cls) el.className = cls; return el; }
function showTab(tab) { currentTab = tab; document.querySelectorAll('.panel').forEach(p => p.hidden = p.id !== `panel-${tab}`); document.querySelectorAll('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.tab === tab)); $('breadcrumb').textContent = {create:'Văn bản thành giọng nói',dub:'Lồng tiếng video',writing:'AI viết kịch bản',clone:'Nhân bản giọng nói',voices:'Thư viện giọng',history:'Lịch sử bản thu'}[tab]; notify(''); if(tab === 'history') refreshHistory().catch(e=>notify(e.message,true)); if(tab === 'voices') renderVoices(); if(tab==='dub'){refreshDubSources().catch(e=>notify(e.message,true));} if(tab==='dub')$('dub-settings').textContent=`Nhịp đọc: ${$('speed').value}× · ${$('delivery').selectedOptions[0].textContent}. Chọn giọng lồng tiếng trực tiếp bên dưới.`; }
document.querySelectorAll('[data-tab]').forEach(b=>b.addEventListener('click',()=>{userNavigated=true;showTab(b.dataset.tab);}));
function updateVoiceOptions() { const previous = $('voice').value; const available = voices.filter(v=>v.languages.includes($('language').value)&&($('voice-source').value==='all'||($('voice-source').value==='system'?(v.engine==='system'):(v.engine!=='system')))); $('voice').replaceChildren(...available.map(v=>{ const o = element('option',v.name + (v.native_language?' · '+(config.languages[v.native_language]||({'en':'Mỹ / Anh'}[v.native_language]||v.native_language)):'') + (v.ready===false?' · Chưa tải model':' · Sẵn sàng') + (v.category === 'cloned' ? ' · Cá nhân' : '')); o.value=v.id; return o; })); if(available.some(v=>v.id===previous)) $('voice').value=previous;else{const ready=isHmongStudio()?available.find(v=>v.ready!==false):(available.find(v=>v.engine==='vieneu_nano'&&config?.nano_ready)||available.find(v=>v.engine==='system'||(v.engine==='vieneu_nano'?config?.nano_ready:config?.models[v.engine])));if(ready)$('voice').value=ready.id;} updateVoice(); }
function updateVoice() { const v=voices.find(v=>v.id===$('voice').value); $('voice-label').textContent=v?.name || 'Chưa có giọng'; $('voice-detail').textContent=v?.description || ''; const engine=v?.engine || ($('language').value==='vi' ? 'vieneu':'qwen_clone'); const ready=engine==='system'?true:engine==='vieneu_nano' ? config?.nano_ready : config?.models[engine]; $('engine-info').textContent=!v?'Chưa có giọng phù hợp. Chọn giọng AI hoặc thêm giọng Windows.':engine==='system'?'Giọng Windows đã cài · không cần model AI':ready?(engine==='hmong_native'?'Hmong nhanh thử nghiệm · Mô hình đã tải':`${engine} · Mô hình đã tải`):(engine==='hmong_native'?'Hmong nhanh thử nghiệm · Cần tải mô hình':`${engine} · Cần tải mô hình`); $('generate').disabled=voiceSubmitting;if(typeof syncVoiceDownload==='function')syncVoiceDownload('create');updateHmongVoiceChoices(); }
function applyStudioVoices(entries){
 const previous=hmongVoiceId||$('voice').value;
 voices=entries;updateVoiceOptions();updateDubVoices();
 if(isHmongStudio()&&!studioInitialized){const preferred=voices.some(v=>v.id===config.default_voice_id)?config.default_voice_id:previous;selectHmongVoice(voices.some(v=>v.id===preferred)?preferred:$('voice').value);}
 renderVoices();updateHmongReferenceNote();
}
async function setDefaultHmongVoice(voice){
 try{await ensureStudioReady();const result=await api('/api/voices/default',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({voice_id:voice.id})});config.default_voice_id=result.default_voice_id||voice.id;selectHmongVoice(config.default_voice_id);renderVoices();notify('Đã đặt “'+voice.name+'” làm giọng mặc định cho lần mở tool sau.');}
 catch(error){notify(error.message,true);throw error;}
}
function hasScriptTimeRanges(text){
 return /(?:^|\n)\s*(?:\d+[.)]?\s+)?[\[('\"“‘]*\s*\d{1,5}:\d{2}(?::\d{2})?(?:[,.]\d{1,3})?[\s\])'\"”’]*(?:-->|->|→|⟶|–>|—>)/m.test(text.replace(/\r\n?/g,'\n').replace(/[\u200b\u200e\u200f\ufeff]/g,''));
}
function updateSubtitleMode(){
 const visible=isHmongStudio()&&$('script-format').value==='srt';
 $('srt-reading-mode').hidden=!visible;$('srt-reading-note').hidden=!visible;
 $('srt-reading-note').textContent=$('create-subtitle-timing').checked?'Giữ đúng mốc từng câu, tự căn tốc độ và giữ đủ lời. Câu quá dài có thể đọc nhanh; vượt giới hạn sẽ báo rõ câu cần nới mốc, không cắt chữ.':'Chỉ đọc lời Hmong, bỏ số thứ tự và mốc giờ; không thêm khoảng chờ theo phụ đề. Bật giữ mốc khi cần căn thời gian.';
}
$('script-format').addEventListener('change',updateSubtitleMode);
$('create-subtitle-timing').addEventListener('change',updateSubtitleMode);
async function refreshVoices(){applyStudioVoices((await api('/api/voices')).voices);}
function renderVoices() { const search=$('voice-search').value.toLocaleLowerCase(); const list=voices.filter(v=>v.name.toLocaleLowerCase().includes(search)); $('voice-library').replaceChildren(); if(!list.length) $('voice-library').append(element('div','Chưa có giọng phù hợp. Hãy thêm giọng cá nhân.','empty')); for(const v of list) { const card=element('article',undefined,'voice-card card'); card.append(element('span','≋','voice-orb'),element('h3',v.name),element('p',v.description)); const tags=element('div',undefined,'tags'); tags.append(element('span',v.category==='cloned'?'GIỌNG CÁ NHÂN':'GIỌNG CÓ SẴN','tag')); for(const lang of v.languages.slice(0,4)) tags.append(element('span',config.languages[lang]||lang,'tag')); if(v.languages.length>4) tags.append(element('span',`+${v.languages.length-4}`,'tag')); if(isNativeHmong()&&config.default_voice_id===v.id)tags.append(element('span','MẶC ĐỊNH','tag')); card.append(tags); if(v.category==='cloned'||v.sample_url) { const audio=element('audio'); audio.controls=true; audio.preload='none'; audio.src=v.sample_url||`/api/voices/${v.id}/sample`; card.append(audio); } const actions=element('div',undefined,'voice-actions'); const use=element('button','Sử dụng giọng →'); use.onclick=()=>{ selectLibraryVoice(v); showTab('create'); $('script').focus(); }; actions.append(use); if(isNativeHmong()&&['hmong_native','f5_hmong'].includes(v.engine)&&v.languages.includes('mww')){const preferred=element('button',config.default_voice_id===v.id?'Giọng mặc định':'Đặt làm giọng mặc định');preferred.disabled=config.default_voice_id===v.id;preferred.dataset.defaultVoice=v.id;preferred.onclick=async()=>{preferred.disabled=true;try{await setDefaultHmongVoice(v);}catch{preferred.disabled=false;}};actions.append(preferred);} if(v.category==='cloned') { const del=element('button','Xóa','delete'); del.onclick=async()=>{if(!confirm(`Xóa mẫu và hồ sơ giọng “${v.name}”?`))return; try{await api(`/api/voices/${v.id}`,{method:'DELETE'});if(config.default_voice_id===v.id)config.default_voice_id=null; await refreshVoices();}catch(e){notify(e.message,true);} }; actions.append(del); } card.append(actions); $('voice-library').append(card); } }
$('voice-search').oninput=renderVoices;
$('language').onchange=updateVoiceOptions; $('voice').onchange=()=>{if(isHmongStudio())selectHmongVoice($('voice').value);else updateVoice();};
$('script').oninput=()=>{$('char-count').textContent=`${scriptCharacterCount($('script').value).toLocaleString('vi-VN')} / ${scriptCharacterLimit().toLocaleString('vi-VN')} ký tự`;if(isHmongStudio()&&hasScriptTimeRanges($('script').value))$('script-format').value='srt';updateSubtitleMode();};
updateScriptLimits();
$('sample-button').onclick=()=>{$('script').value=samples[$('language').value]||samples['en-US']; $('script').oninput();};
$('speed').oninput=()=>{$('speed-value').textContent=Number($('speed').value).toFixed(2)+'×';};
function jobDownloadExtension(job){return job.longform?'zip':(job.format||'wav');}
function jobDownloadUrl(job){return job.longform?`/api/jobs/${job.id}/archive`:(job.url||'');}
function jobPreviewUrl(job,index){
 if(!job.longform)return job.url||'';
 const chapters=Array.isArray(job.chapters)?job.chapters:[],chapter=chapters.find(part=>Number(part.index)===Number(index))||chapters[0];
 return chapter?`/api/jobs/${job.id}/chapters/${chapter.index}`:'';
}
function renderJobAudio(job,audio,download,chapterSelect){
 const done=job.status==='done',chapters=Array.isArray(job.chapters)?job.chapters:[];
 let select=chapterSelect||audio._chapterSelect;
 if(job.longform&&!select){select=element('select');select.className='secondary-button';select.setAttribute('aria-label','Chọn phần để nghe');audio.before(select);audio._chapterSelect=select;}
 const choose=()=>{const url=done?jobPreviewUrl(job,select?.value):'';if(audio.getAttribute('src')!==(url||null)){audio.pause();if(url)audio.src=url;else audio.removeAttribute('src');}audio.hidden=!url;return url;};
 if(select){
  const previous=select.dataset.jobId===job.id?select.value:'';
  select.replaceChildren(...chapters.map(chapter=>{const option=element('option',`Phần ${chapter.index} · ${Number(chapter.characters||0).toLocaleString('vi-VN')} ký tự · ${duration(chapter.audio_seconds||0)}`);option.value=String(chapter.index);return option;}));
  if(chapters.some(chapter=>String(chapter.index)===previous))select.value=previous;
  select.dataset.jobId=job.id;select.hidden=!done||!job.longform||!chapters.length;select.onchange=choose;
  const label=select.id?document.querySelector('label[for="'+select.id+'"]'):null;if(label)label.hidden=select.hidden;
 }
 if(download){const url=done?jobDownloadUrl(job):'';download.hidden=!url;if(url){download.href=url;download.download=`voice-studio-${job.id.slice(0,8)}.${jobDownloadExtension(job)}`;download.textContent=job.longform?`Tải ZIP · ${chapters.length} phần ${(job.format||'wav').toUpperCase()} ↓`:`Tải ${(job.format||'wav').toUpperCase()} ↓`;}else download.removeAttribute('href');}
 return choose();
}
function setOutput(job) { if(activeOutputId && activeOutputId!==job.id)return;if(job.video_id||dubJob===job.id)updateDub(job);$('voice-progress').value=job.progress||0;$('voice-percent').textContent=`${job.progress||0}%`;const working=['queued','running','cancelling'].includes(job.status);$('stop-generation').hidden=!working;$('stop-generation').disabled=job.status==='cancelling';$('stop-generation').textContent=job.status==='cancelling'?'Đang dừng…':'■ Dừng tạo giọng'; $('output-title').textContent = {queued:'Bản thu đang trong hàng đợi…',running:'AI đang tạo giọng nói trên máy…',cancelling:'Đang dừng…',cancelled:'Đã dừng · Có thể tiếp tục trong Lịch sử',error:'Chưa tạo được bản thu',done:'Bản thu của bạn đã sẵn sàng'}[job.status]; voiceFeedback(job.error||({queued:'Yêu cầu đã nhận. Bản thu đang trong hàng đợi…',running:'Đang tạo giọng: '+(job.phase||'đang xử lý')+' · '+(job.progress||0)+'%',cancelling:'Đang dừng tạo giọng…',cancelled:'Đã dừng tạo giọng. Có thể tiếp tục trong Lịch sử.',error:'Chưa tạo được bản thu.',done:'Bản thu đã sẵn sàng. Nghe thử hoặc tải tệp bên dưới.'+(Array.isArray(job.timing_warnings)&&job.timing_warnings.length?' '+job.timing_warnings.join(' '):'')}[job.status]||job.status),job.status==='error'); $('output-subtitle').textContent=job.error || `${job.voice_name} · ${job.phase || ''} · ${job.progress || 0}% · ${duration(job.audio_seconds || 0)}${job.longform?' · '+(job.chapters?.length||job.chapter_count||0)+' phần · tải trọn bộ ZIP':''}${job.duration_limited ? ' · Đã đạt giới hạn; còn nội dung chưa đọc' : ''}`;showSpeedReport(job);renderJobAudio(job,$('output-audio'),$('download'),$('output-chapter')); }
$('generate').onclick=async()=>{
 if(voiceSubmitting)return;
 voiceSubmitting=true;const attempt=++voiceAttempt;activeOutputId='attempt-'+attempt;$('generate').disabled=true;notify('');
 $('stop-generation').hidden=true;$('output-audio').pause();for(const id of ['output-audio','download','output-chapter'])$(id).hidden=true;const chapterLabel=document.querySelector('label[for="output-chapter"]');if(chapterLabel)chapterLabel.hidden=true;$('voice-progress').value=0;$('voice-percent').textContent='0%';
 voiceFeedback(studioReady?'Đang kiểm tra lời và giọng đã chọn…':'Đang kết nối studio và kiểm tra giọng…',false,'Đang chuẩn bị bản thu');
 try{
  await ensureStudioReady();
  const text=$('script').value,voice=voices.find(v=>v.id===$('voice').value);
  if(!text.trim()){$('script').focus();throw Error('Hãy nhập nội dung cần đọc.');}
  if(scriptCharacterCount(text)>scriptCharacterLimit())throw Error('Tối đa '+scriptCharacterLimit().toLocaleString('vi-VN')+' ký tự.');
  if(!voice||voice.ready===false){const message=voice?'Giọng chưa tải model. Bấm Tải model giọng đã chọn, chờ Sẵn sàng rồi tạo lại.':'Chưa có giọng phù hợp. Chọn lại bộ lọc hoặc bấm Chọn giọng AI phù hợp.';$('voice-model-status').textContent=message;throw Error(message);}
  voiceFeedback('Đang gửi yêu cầu tạo giọng…',false,'Đang gửi yêu cầu tạo giọng');
  const job=await api('/api/speech',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({input_format:$('script-format').value,subtitle_timing:!isHmongStudio()||$('create-subtitle-timing').checked,skip_timestamps:$('create-skip-times').checked,text,voice_id:voice.id,language:$('language').value,speed:Number($('speed').value),format:$('format').value,max_minutes:Number($('max-minutes').value),delivery:$('delivery').value,paragraph_pause:Number($('paragraph-pause').value),quality:$('quality').value,nano_steps:Number($('nano-steps').value),nano_threads:Number($('nano-threads').value),nano_parallel:Number($('nano-parallel').value)})});
  if(attempt!==voiceAttempt)return;activeOutputId=job.id;setOutput(job);pollJob(job.id);
 }catch(error){if(attempt===voiceAttempt){if(error.field==='text')$('script').focus({preventScroll:true});voiceFeedback(error.message,true,'Chưa tạo được bản thu');}}
 finally{voiceSubmitting=false;$('generate').disabled=false;}
};
async function pollJob(id){
 if(activeOutputId!==id)return;
 let job;try{job=await api('/api/jobs/'+id);if(activeOutputId!==id)return;setOutput(job);if(currentTab==='history')await refreshHistory();}
 catch(error){if(activeOutputId!==id)return;voiceFeedback('Mất kết nối theo dõi tác vụ. Đang thử lại: '+error.message,true,'Đang kết nối lại để theo dõi bản thu');setTimeout(()=>pollJob(id),2000);return;}
 if(activeOutputId===id&&['queued','running','cancelling'].includes(job.status))setTimeout(()=>pollJob(id),job.status==='cancelling'?200:1000);
}
let cloneReference={token:0,url:null,file:null,duration:0,pending:false,ready:false,prefilled:null};
let cloneInspectionPromise=null,cloneSubmitting=false;
function cloneStatus(message,error=false,busy=false){const node=$('clone-status');node.textContent=message;node.hidden=!message;node.classList.toggle('error-message',error);$('clone-progress').hidden=!busy;}
function voiceQualityAdvice(voice){const quality=voice.quality||{},messages=[];for(const value of [quality.advisories,quality.guidance])for(const item of Array.isArray(value)?value:[value]){const message=typeof item==='string'?item:item?.message;if(message&&!messages.includes(message))messages.push(message);}return messages.join(' ');}
function cloneButtonsBusy(busy){$('clone-submit').disabled=busy;$('clone-save-test').disabled=busy;}
function resetCloneReference(){const token=cloneReference.token+1;if(cloneReference.url)URL.revokeObjectURL(cloneReference.url);const audio=$('clone-reference-audio');audio.pause();audio.removeAttribute('src');audio.hidden=true;cloneReference={token,url:null,file:null,duration:0,pending:false,ready:false,prefilled:null};for(const id of ['clone-reference-start','clone-reference-end']){$(id).value='';$(id).disabled=true;$(id).setCustomValidity('');}$('clone-listen-clip').disabled=true;$('clone-reference-info').textContent='Chọn tệp để kiểm tra và chọn đoạn tham chiếu 3–8 giây.';}
function selectedCloneClip(){const start=Number($('clone-reference-start').value),end=Number($('clone-reference-end').value);if(!cloneReference.ready||!Number.isFinite(start)||!Number.isFinite(end)||start<0||end>cloneReference.duration+.001||end-start<3||end-start>8+.001)throw Error('Chọn đoạn mẫu dài 3–8 giây, nằm trong thời lượng tệp.'+(isNativeHmong()?'':' Lời Hmong phải khớp đúng đoạn được chọn.'));return {start,end};}
function cloneClipChanged(){
 if(!isHmongStudio()||!cloneReference.ready)return;
 const prefilled=cloneReference.prefilled;let message;
 try{
  const clip=selectedCloneClip();$('clone-reference-end').setCustomValidity('');
  const same=prefilled&&Math.abs(clip.start-prefilled.start)<.001&&Math.abs(clip.end-prefilled.end)<.001;
  if(!same&&prefilled&&$('transcript').value===prefilled.text)$('transcript').value='';
  if(same&&!$('transcript').value)$('transcript').value=prefilled.text;
  const note=same?(prefilled.textVerified?'Đoạn đang chọn dùng lời mẫu do bạn cung cấp và xác nhận. Bạn có thể nghe và sửa.':'Lời gợi ý cho đoạn này chưa được xác minh khớp âm thanh; hãy nghe kiểm tra và sửa nếu cần.'):(isNativeHmong()?'Mẫu có thể nói ngôn ngữ bất kỳ. Lời mẫu không bắt buộc; tool dùng âm thanh này để lấy chất giọng.':'Nhập lời Hmong khớp chính xác đoạn đang chọn.');
  message=`Tệp ${cloneReference.duration.toFixed(2)} giây · đang chọn ${clip.start.toFixed(2)}–${clip.end.toFixed(2)} giây (${(clip.end-clip.start).toFixed(2)} giây). `+note;
 }catch(e){$('clone-reference-end').setCustomValidity(e.message);if(prefilled&&$('transcript').value===prefilled.text)$('transcript').value='';message=e.message;}
 $('clone-reference-info').textContent=message;
}
$('transcript').addEventListener('input',()=>{if(isHmongStudio()&&cloneReference.prefilled){if($('transcript').value!==cloneReference.prefilled.text)$('clone-reference-info').textContent='Bạn đang sửa lời mẫu. Kiểm tra lời khớp đoạn thu trước khi lưu.';else cloneClipChanged();}});
async function inspectCloneFile(file){
 resetCloneReference();cloneButtonsBusy(cloneSubmitting);$('transcript').value='';
 if(!file){cloneStatus('');return;}
 if(file.size>20*1024*1024){cloneStatus('Mẫu âm thanh vượt quá 20 MB.',true);return;}
 const token=cloneReference.token;cloneReference.file=file;cloneReference.pending=true;
 cloneButtonsBusy(true);cloneStatus('Đang kết nối studio và kiểm tra mẫu âm thanh…',false,true);
 try{
  await ensureStudioReady();
  if(token!==cloneReference.token||$('clone-file').files[0]!==file)return;
  if(!isHmongStudio()){cloneStatus('');return;}
  const data=new FormData();data.append('file',file);
  const info=await api('/api/hmong/reference-info',{method:'POST',body:data});
  if(token!==cloneReference.token||$('clone-file').files[0]!==file)return;
  const duration=Number(info.duration);
  if(!Number.isFinite(duration)||duration<3||duration>30.02)throw Error('Chọn tệp âm thanh dài 3–30 giây, rồi lấy đoạn mẫu 3–8 giây.');
  cloneReference.duration=duration;cloneReference.ready=true;cloneReference.url=URL.createObjectURL(file);
  const audio=$('clone-reference-audio');audio.src=cloneReference.url;audio.hidden=false;
  for(const id of ['clone-reference-start','clone-reference-end']){$(id).disabled=false;$(id).max=String(duration);}
  $('clone-reference-start').value=String(info.reference_start??0);$('clone-reference-end').value=String(info.reference_end??Math.min(5,duration));$('clone-listen-clip').disabled=false;
  if(info.automatic&&info.known_preset&&info.transcript){
   cloneReference.prefilled={start:Number(info.reference_start),end:Number(info.reference_end),text:info.transcript,textVerified:info.transcript_verified===true};$('transcript').value=info.transcript;
   if(!$('clone-name').value.trim())$('clone-name').value=(voices.find(v=>v.id===info.known_preset)?.name||'Giọng Hmong')+' · Cá nhân';
  }
  cloneClipChanged();
  cloneStatus(info.automatic&&info.transcript?(info.transcript_verified===true?'Đã đối chiếu đúng tệp MP3 gốc và điền lời mẫu do bạn cung cấp, xác nhận khớp đoạn thu. Có thể nghe, sửa rồi lưu hoặc tạo thử.':'Đã đối chiếu đúng tệp MP3 gốc. Lời gợi ý được điền nhưng chưa được xác minh; hãy nghe và sửa cho khớp trước khi lưu hoặc tạo thử.'):(isNativeHmong()?(info.automatic_selection?'Đã gợi ý đoạn có tín hiệu tiếng nói. Nghe lại đoạn đang chọn rồi lưu và tạo thử tiếng Hmong; có thể sửa mốc, không cần nhập lời mẫu.':'Đã kiểm tra tệp. Chọn đoạn 3–8 giây rõ tiếng, rồi lưu và tạo thử tiếng Hmong. Không cần nhập lời mẫu.'):'Đã kiểm tra tệp. Chọn đoạn 3–8 giây, nghe thử và nhập đúng lời Hmong trong đoạn đó.'));
 }catch(error){if(token===cloneReference.token)cloneStatus(error.message,true);}
 finally{if(token===cloneReference.token){cloneReference.pending=false;cloneButtonsBusy(cloneSubmitting);$('clone-progress').hidden=true;}}
}
$('clone-file').addEventListener('change',()=>{cloneInspectionPromise=inspectCloneFile($('clone-file').files[0]);});
for(const id of ['clone-reference-start','clone-reference-end'])$(id).addEventListener('input',cloneClipChanged);
$('clone-listen-clip').onclick=async()=>{try{const clip=selectedCloneClip();const audio=$('clone-reference-audio');audio.currentTime=clip.start;await audio.play();}catch(e){cloneStatus('Không phát được đoạn mẫu: '+e.message,true);}};
$('clone-reference-audio').addEventListener('timeupdate',()=>{const audio=$('clone-reference-audio'),end=Number($('clone-reference-end').value);if(cloneReference.ready&&audio.currentTime>=end)audio.pause();});
function addSavedVoice(voice){
 const language=voice.language||voice.languages?.[0]||$('clone-language').value;
 const engine=voice.engine||(language==='vi'?'vieneu':'qwen_clone');
 const entry={...voice,category:'cloned',engine,languages:voice.languages||[language],native_language:voice.native_language||language,ready:voice.ready??(config.models[engine]===true)};
 // A confirmed POST is durable. Index refresh is not a prerequisite for using
 // this record, and a later GET failure must never turn it into a failed save.
 applyStudioVoices([...voices.filter(item=>item.id!==entry.id),entry]);
 return entry;
}
$('clone-form').onsubmit=async(e)=>{
 e.preventDefault();if(cloneSubmitting)return;cloneSubmitting=true;cloneButtonsBusy(true);
 let hmong=false;
 try{
  await ensureStudioReady();hmong=isHmongStudio();
  if(cloneInspectionPromise)await cloneInspectionPromise;
  const file=$('clone-file').files[0];
  if(!file)throw Error('Chọn tệp âm thanh để lưu giọng.');
  if(file.size>20*1024*1024)throw Error('Mẫu âm thanh vượt quá 20 MB.');
  const test=hmong&&e.submitter?.id==='clone-save-test',data=new FormData(e.target);
  if(hmong){
   if(!cloneReference.pending&&(!cloneReference.ready||cloneReference.file!==file))await inspectCloneFile(file);
   if(cloneReference.pending||!cloneReference.ready||cloneReference.file!==file)throw Error('Chưa kiểm tra được mẫu âm thanh. Chọn lại tệp rồi thử lưu.');
   const clip=selectedCloneClip();data.set('reference_start',String(clip.start));data.set('reference_end',String(clip.end));
   if(!isNativeHmong()&&!$('transcript').value.trim())throw Error('Nhập chính xác lời Hmong của đoạn mẫu đang chọn.');
  }
  $('clone-file').disabled=true;notify('');if(hmong)cloneStatus('Đang cắt đoạn mẫu, chuẩn hóa âm thanh và lưu hồ sơ giọng…',false,true);
  const voice=addSavedVoice(await api('/api/voices/clone',{method:'POST',body:data}));
  const advice=voiceQualityAdvice(voice),savedAdvice=advice?' '+advice:'';
  e.target.reset();
  if(hmong){
   resetCloneReference();selectHmongVoice(voice.id);showTab('create');
   if(test){
    $('script-format').value='txt';updateSubtitleMode();$('script').value='Nyob zoo. Ua tsaug rau koj mloog.';$('script').oninput();
    cloneStatus(`Đã lưu “${voice.name}”. Đang gửi yêu cầu tạo bản thu thử Hmong.${savedAdvice}`);await $('generate').onclick();
    if(advice)notify(`Đã lưu “${voice.name}”. ${advice}`);
   }else{
    cloneStatus(`Đã lưu hồ sơ “${voice.name}”.${savedAdvice}`);
    notify(`Đã lưu “${voice.name}” và chọn giọng này. Nhập lời rồi bấm Tạo giọng để tạo bản thu thật.${savedAdvice}`);$('script').focus();
   }
  }else{showTab('voices');notify(`Đã lưu mẫu giọng “${voice.name}”. Chọn Sử dụng giọng để tạo lời đọc sau khi tải mô hình.${savedAdvice}`);}
 }catch(error){cloneStatus(error.message,true);notify(error.message,true);}
 finally{cloneSubmitting=false;$('clone-file').disabled=false;cloneButtonsBusy(false);$('clone-progress').hidden=true;}
};
async function refreshHistory() { const items=(await api('/api/history')).items; $('history-list').replaceChildren(); if(!items.length){$('history-list').append(element('div','Chưa có bản thu. Hãy bắt đầu với câu chuyện đầu tiên của bạn.','empty'));return;} for(const item of items) { const card=element('article',undefined,'history-item card');const head=element('div',undefined,'history-head');head.append(element('span',`${item.voice_name} · ${config.languages[item.language]} · ${new Date(item.created_at).toLocaleString('vi-VN')}`),element('span',{queued:'Trong hàng đợi',running:'Đang tạo',done:'Hoàn tất',cancelled:'Đã dừng',cancelling:'Đang dừng',error:'Có lỗi'}[item.status],`status ${item.status}`)); card.append(head,element('p',item.text.length>3000 ? item.text.slice(0,3000)+'…' : item.text));card.append(element('p',`${item.phase || ''} · ${item.progress || 0}% · ${duration(item.audio_seconds || 0)}${item.duration_limited ? ' · Đã đạt giới hạn thời lượng; còn văn bản chưa đọc.' : ''}`,'form-note')); if(item.error)card.append(element('p',item.error,'error-message')); const controls=element('div',undefined,'history-controls'); if(item.status==='done') {const audio=element('audio');audio.controls=true;audio.preload='none';const link=element('a',undefined,'secondary-button');controls.append(audio,link);renderJobAudio(item,audio,link);for(const extension of (item.longform?['txt']:['txt','srt'])){const scriptLink=element('a',item.longform?'Xuất kịch bản gốc TXT':'Xuất '+extension.toUpperCase(),'secondary-button');scriptLink.href=`/api/jobs/${item.id}/script.${extension}`;scriptLink.download='script.'+extension;controls.append(scriptLink);}if(item.video_url){const videoLink=element('a','Tải video MP4 ↓','secondary-button');videoLink.href=item.video_url;videoLink.download='voice-studio-'+item.id.slice(0,8)+'.mp4';controls.append(videoLink);}} if(['running','queued','cancelling'].includes(item.status)){const stop=element('button','Dừng');stop.disabled=item.status==='cancelling';stop.onclick=async()=>{try{await api(`/api/jobs/${item.id}/cancel`,{method:'POST'});await refreshHistory();}catch(e){notify(e.message,true);}};controls.append(stop);} if(['error','cancelled'].includes(item.status)){const resume=element('button','Tiếp tục');resume.onclick=async()=>{try{const job=await api(`/api/jobs/${item.id}/resume`,{method:'POST'});activeOutputId=job.id;setOutput(job);pollJob(job.id);await refreshHistory();}catch(e){notify(e.message,true);}};controls.append(resume);} if(!['running','queued','cancelling'].includes(item.status)){const del=element('button','Xóa bản thu');del.onclick=async()=>{if(!confirm('Xóa bản thu này khỏi máy?'))return;try{await api(`/api/history/${item.id}`,{method:'DELETE'});await refreshHistory();}catch(e){notify(e.message,true);}};controls.append(del);}card.append(controls);$('history-list').append(card);} if(items.some(i=>['queued','running','cancelling'].includes(i.status))&&!polling){polling=true;setTimeout(()=>{polling=false;if(currentTab==='history')refreshHistory().catch(e=>notify(e.message,true));},3000);} }
$('help-button').onclick=()=>{$('help-dialog').showModal();};$('close-help').onclick=()=>{$('help-dialog').close();};
// GET reads may verify large local model files on a slow disk. Keep their
// progress visible instead of aborting them and starting overlapping scans.
async function readStudioBootstrap(path){return api(path);}
async function ensureStudioReady(refresh=false){
 if(studioBootstrapPromise)return studioBootstrapPromise;
 if(studioReady&&!refresh)return;
 studioRetry.hidden=true;studioRetry.disabled=true;
 if(!voiceSubmitting)voiceFeedback('Đang kết nối studio và kiểm tra giọng…');
 studioBootstrapPromise=(async()=>{
  let nextConfig,nextVoices;
  for(let attempt=0;attempt<2;attempt++){
   try{nextConfig=await readStudioBootstrap('/api/config');const response=await readStudioBootstrap('/api/voices');if(!nextConfig.languages||!nextConfig.models||!Array.isArray(response.voices))throw Error('Dữ liệu studio chưa đầy đủ. Thử kết nối lại.');nextVoices=response.voices;break;}
   catch(error){if(attempt===1)throw error;await new Promise(resolve=>setTimeout(resolve,300));}
  }
  // Publish config and voices together, then apply the variant once. Failed reads
  // leave the draft and the last working voice settings intact.
  config=nextConfig;voices=nextVoices;
  for(const id of ['language','clone-language','writing-language','dub-language']){
   const select=$(id),previous=select.value;select.replaceChildren(...Object.entries(config.languages).filter(([value])=>id!=='clone-language'||config.ai_voice_languages.includes(value)).map(([value,label])=>new Option(label,value)));
   if([...select.options].some(option=>option.value===previous))select.value=previous;else if([...select.options].some(option=>option.value===config.default_language))select.value=config.default_language;
  }
  if(!studioInitialized)applyStudioVariant();
  updateScriptLimits();$('hardware').textContent=config.hardware_label||config.hardware+' LOCAL';
  $('model-status').replaceChildren(...Object.entries(config.models).map(([name,ready])=>element('p',(ready?'●':'○')+' '+name+': '+(ready?'Đã tải':'Chưa tải'))));
  applyStudioVoices(nextVoices);studioInitialized=true;studioReady=true;studioRetry.hidden=true;
  if(!voiceSubmitting){voiceFeedback('Studio đã sẵn sàng. Nhập lời, chọn giọng rồi bấm Tạo giọng nói.');notify('');}
 })().catch(error=>{studioRetry.hidden=false;voiceFeedback('Không kết nối được studio: '+error.message,true);throw error;}).finally(()=>{studioBootstrapPromise=null;studioRetry.disabled=false;});
 return studioBootstrapPromise;
}
async function init(){
 try{await ensureStudioReady();const recent=(await api('/api/history')).items[0];if(recent&&voiceAttempt===0&&!activeOutputId){activeOutputId=recent.id;setOutput(recent);if(['running','queued','cancelling'].includes(recent.status))pollJob(recent.id);}}
 catch(error){if(studioReady)notify(error.message,true);}
}
init();
loadConnections().catch(e=>notify(e.message,true));

function duration(seconds){seconds=Math.floor(seconds);return `${Math.floor(seconds/3600)}:${String(Math.floor(seconds/60)%60).padStart(2,'0')}:${String(seconds%60).padStart(2,'0')}`;}
let connections;
async function loadConnections(){connections=await api('/api/writing/connections');refreshConnectionLabel();}
function refreshConnectionLabel(){const provider=$('writing-provider').value;const local=provider==='ollama';$('cloud-key-fields').hidden=local;$('local-writing-help').hidden=!local;$('disconnect-writing').hidden=local;$('writing-connected').textContent=connections?.providers[provider] ? (local?'Ollama đang chạy':'Đã kết nối') : (local?'Chưa mở Ollama':'Chưa kết nối');const available=connections?.local?.models || [];const previous=$('writing-model').value;const preferred=connections?.defaults[provider] || (local?'qwen3:4b':'');$('writing-model').value=local && available.length ? (available.includes(previous)?previous:(available.includes(preferred)?preferred:available[0])) : preferred;$('local-writing-models').replaceChildren(...(connections?.local?.models || []).map(name=>{const o=element('option');o.value=name;return o;}));}
$('writing-provider').onchange=()=>{$('writing-key').value='';refreshConnectionLabel();};
$('connect-writing').onclick=async()=>{const button=$('connect-writing');button.disabled=true;notify('');try{await api('/api/writing/connect',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({provider:$('writing-provider').value,api_key:$('writing-key').value})});$('writing-key').value='';await loadConnections();notify($('writing-provider').value==='ollama' ? 'Đã kết nối Ollama cục bộ. Không cần API key. Kiểm tra model đã tải trong danh sách tên model.' : 'Kết nối thành công. Khóa chỉ giữ trong bộ nhớ máy chủ.');}catch(e){notify(e.message,true);}finally{button.disabled=false;}};
$('disconnect-writing').onclick=async()=>{try{await api(`/api/writing/connections/${$('writing-provider').value}`,{method:'DELETE'});await loadConnections();}catch(e){notify(e.message,true);}};
$('write-script').onclick=async()=>{if(!$('writing-prompt').value.trim()){notify('Nhập chủ đề hoặc nội dung cần viết.',true);return;}const button=$('write-script');button.disabled=true;notify('AI đang viết; CPU có thể cần vài phút. Không đóng ứng dụng hoặc Ollama.');try{const result=await api('/api/writing/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({provider:$('writing-provider').value,model:$('writing-model').value,prompt:$('writing-prompt').value,language:$('writing-language').value,kind:$('writing-kind').value,minutes:Number($('writing-minutes').value)})});$('writing-result').value=result.text;notify((result.incomplete?'Kết quả đã chạm giới hạn trả lời. ':'')+result.note);}catch(e){notify(e.message,true);}finally{button.disabled=false;}};
function transferWriting(append){const text=$('writing-result').value.trim();if(!text){notify('Chưa có kết quả để chuyển.',true);return;}const combined=append ? $('script').value+'\n\n'+text : text;if(scriptCharacterCount(combined)>scriptCharacterLimit()){notify('Tổng kịch bản vượt '+scriptCharacterLimit().toLocaleString('vi-VN')+' ký tự.',true);return;}$('script').value=combined;$('language').value=$('writing-language').value;updateVoiceOptions();$('script').oninput();showTab('create');}
$('use-writing').onclick=()=>transferWriting(false);$('append-writing').onclick=()=>transferWriting(true);
$('continue-writing').onclick=()=>{const text=$('writing-result').value.trim();if(!text){notify('Chưa có nội dung để viết tiếp.',true);return;}$('writing-prompt').value='Viết tiếp phần sau, không lặp lại nội dung đã có. Tiếp tục theo chương. Phần cuối trước đó:\n'+text.slice(-12000);$('writing-prompt').focus();notify('Đã chuẩn bị yêu cầu viết tiếp. Bấm Viết kịch bản để gửi.');};

$('stop-generation').onclick=async()=>{if(!activeOutputId)return;const button=$('stop-generation');button.disabled=true;try{const job=await api(`/api/jobs/${activeOutputId}/cancel`,{method:'POST'});setOutput(job);notify('Đã yêu cầu dừng. Các đoạn hoàn tất được giữ để tiếp tục.');}catch(e){notify(e.message,true);}finally{if(button.textContent!=='Đang dừng…')button.disabled=false;}};
document.querySelectorAll('[data-provider]').forEach(button=>button.onclick=()=>{$('writing-provider').value=button.dataset.provider;$('writing-provider').onchange();if(button.dataset.provider!=='ollama')$('writing-key').focus();});

$('use-nano').onclick=()=>{if(!config?.nano_ready){notify('Chạy download_turbo_model.bat để tải Nano, rồi tải lại trang. Nano ưu tiên tốc độ, chất lượng thấp hơn Turbo.',true);return;}$('language').value='vi';$('voice-source').value='all';updateVoiceOptions();$('voice').value='nano-minhquan';$('quality').value='auto';updateVoice();notify('Đã chọn Minh Quân · Siêu nhanh (Nano). Giọng này khác giọng trước và ưu tiên tốc độ hơn độ tự nhiên.');};

function showSpeedReport(job){
 const report=job.speed_report,el=$('performance-result');
 if(!report){el.hidden=true;return;}
 const speechBasis=report.measurement_basis==='speech_chunks_excluding_inserted_silence';
 const verified=speechBasis&&report.target_30x_verified_one_hour===true;
 const sustained=speechBasis&&report.sustained_measurement===true;
 let conclusion;
 if(verified)conclusion='Lượt này đã tạo ít nhất 1 giờ lời đọc trong tối đa 120 giây.';
 else if(!speechBasis)conclusion='Báo cáo cũ tính cả thời lượng đầu ra; không dùng để xác minh mục tiêu 30×.';
 else if(!sustained)conclusion='Mẫu dưới 60 giây lời đọc, chưa đủ để kết luận tốc độ duy trì hoặc mục tiêu 1 giờ / 2 phút.';
 else if(report.target_30x_met_on_sample)conclusion='Mẫu này đạt 30×; chưa kiểm chứng tạo đủ 1 giờ trong 2 phút.';
 else conclusion='Mẫu này chưa đạt mục tiêu 30× (1 giờ lời đọc / 2 phút xử lý).';
 el.hidden=false;el.classList.toggle('error',sustained&&!report.target_30x_met_on_sample);
 const basis=speechBasis?'lời đọc, đã loại thời gian nghỉ/phụ đề chèn thêm':'âm thanh đầu ra';
 const estimate=verified?'':` Ước tính 1 giờ: ${Math.round(report.estimated_hour_seconds)} giây; đây là ngoại suy, phụ thuộc máy, giọng và chất lượng.`;
 el.textContent=`Đã đo${isHmongStudio()?' Hmong':''}: ${report.realtime_multiplier}× thời gian thực trên ${report.measurement_audio_seconds}s ${basis} / ${report.measurement_elapsed_seconds}s xử lý (không tính chờ hàng đợi). ${conclusion}${estimate}`;
}
function applyTargetPreset(){if(!config?.nano_ready){notify('Cần tải Nano bằng download_turbo_model.bat, rồi tải lại trang.',true);return false;}$('language').value='vi';$('voice-source').value='all';updateVoiceOptions();$('voice').value='nano-minhquan';$('quality').value='auto';$('nano-steps').value='4';$('nano-threads').value='2';$('nano-parallel').value=(config.cpu_cores>=4&&config.available_ram_gb>=4?'4':config.cpu_cores>=4&&config.available_ram_gb>=3?'2':'1');$('nano-threads').value=$('nano-parallel').value==='4'?'1':'2';$('speed').value='1';$('speed').oninput();$('delivery').value='natural';$('paragraph-pause').value='0';$('format').value='wav';updateVoice();notify('Đã chọn cấu hình bản nháp ưu tiên tốc độ: Minh Quân Nano 4 bước, WAV, nhịp tự nhiên 1×, không thêm nghỉ giữa câu. Có thể giảm độ rõ/tự nhiên; chạy song song tốn thêm RAM. Chưa bảo đảm đạt 30× trên máy này.');return true;}
$('target-preset').onclick=applyTargetPreset;
$('benchmark-speed').onclick=async()=>{if(isHmongStudio()){const voice=voices.find(v=>v.id===$('voice').value);if(!voice||voice.ready===false){notify('Chọn giọng Hmong sẵn sàng trước khi đo tốc độ.',true);return;}const button=$('benchmark-speed');button.disabled=true;try{const job=await api('/api/speech',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:hmongPronunciationSample,voice_id:voice.id,language:'mww',quality:'auto',format:'wav',speed:1,delivery:'natural',paragraph_pause:0,max_minutes:3})});activeOutputId=job.id;setOutput(job);pollJob(job.id);notify('Đang đo bằng câu có ua, thaj, qab, faib, rov, ris. Lời bạn đang soạn được giữ nguyên; nghe kiểm tra phát âm, mẫu ngắn chưa xác minh mục tiêu 1 giờ / 2 phút.');}catch(e){notify(e.message,true);}finally{button.disabled=false;}return;}if(!applyTargetPreset())return;const button=$('benchmark-speed');button.disabled=true;try{const text='Buổi sáng bắt đầu bằng ánh nắng dịu dàng xuyên qua khung cửa. Chúng ta dành một chút thời gian để chuẩn bị cho ngày mới, sắp xếp những công việc quan trọng và giữ tinh thần bình tĩnh. Mỗi bước đi nhỏ đều có thể tạo nên thay đổi tích cực khi được thực hiện đều đặn. Khi gặp khó khăn, hãy tạm dừng, nhìn lại mục tiêu và lựa chọn cách giải quyết phù hợp. Lắng nghe mọi người giúp chúng ta hiểu thêm những góc nhìn khác nhau. Một câu chuyện hay không chỉ cần lời kể rõ ràng mà còn cần cảm xúc chân thành. Công nghệ có thể hỗ trợ công việc sáng tạo, nhưng người kể chuyện vẫn quyết định điều muốn truyền tải. Hãy đọc lại nội dung, sửa những chỗ chưa tự nhiên và kiểm tra âm thanh trước khi chia sẻ. Chất lượng của sản phẩm cuối cùng được tạo nên từ nhiều lần thử và điều chỉnh. Chúc bạn có một ngày làm việc hiệu quả và nhiều ý tưởng mới.';const job=await api('/api/speech',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,voice_id:'nano-minhquan',language:'vi',quality:'auto',nano_steps:4,nano_threads:Number($('nano-threads').value),nano_parallel:Number($('nano-parallel').value),format:'wav',speed:1,delivery:'natural',paragraph_pause:0,max_minutes:3})});activeOutputId=job.id;setOutput(job);pollJob(job.id);notify('Đang tạo mẫu đo riêng; nội dung bạn nhập vẫn được giữ. Khi xong, xem tốc độ và ước tính bên dưới bản thu.');}catch(e){notify(e.message,true);}finally{button.disabled=false;}};

$('machine-info').onclick=async()=>{const button=$('machine-info');button.disabled=true;notify('Đang đọc cấu hình CPU, RAM và khả năng CUDA…');try{const info=await api('/api/system-info');notify(`CPU: ${info.cpu} · ${info.logical_cores || '?'} luồng · RAM: ${info.ram_gb ?? '?'} GB · NVIDIA: ${info.nvidia_gpus.length?info.nvidia_gpus.join('; '):'không phát hiện'} · PyTorch CUDA: ${info.pytorch_cuda_available===true?'dùng được':info.pytorch_cuda_available===false?'chưa dùng được':'chưa xác định'}. ${info.note}`);}catch(e){notify(e.message,true);}finally{button.disabled=false;}};

let dubSource=null,dubJob=null,dubSources=[];
async function refreshDubSources(){dubSources=(await api('/api/videos')).items;const select=$('dub-existing');select.replaceChildren(element('option','Chọn video hoặc tải mới bên dưới'));select.firstChild.value='';for(const item of dubSources){const option=element('option',`${item.name} · ${duration(item.duration)}`);option.value=item.id;select.append(option);}select.value=dubSource?.id||'';if(typeof openVideoEditor==='function')await openVideoEditor();}
$('dub-existing').onchange=()=>{dubSource=dubSources.find(v=>v.id===$('dub-existing').value)||null;$('dub-source').textContent=dubSource?`${dubSource.name} · ${duration(dubSource.duration)} · ${dubSource.codec}`:'Chưa chọn video.';$('dub-delete').hidden=!dubSource;};
$('dub-upload').onclick=async()=>{const file=$('dub-file').files[0];if(!file){notify('Chọn video trước.',true);return;}if(file.size>2*1024**3){notify('Video tối đa 2 GB.',true);return;}if(dubSource){notify('Chọn mục trống trong danh sách video để tải video mới.',true);return;}const b=$('dub-upload');b.disabled=true;$('dub-source').textContent='Đang tải và kiểm tra video…';try{const data=new FormData();data.append('file',file);$('dub-upload-progress').hidden=false;dubSource=await uploadVideo(data);$('dub-source').textContent=`${dubSource.name} · ${duration(dubSource.duration)} · ${dubSource.codec}`;$('dub-delete').hidden=false;await refreshDubSources();}catch(e){$('dub-source').textContent=e.message;notify(e.message,true);}finally{b.disabled=false;}};
$('dub-delete').onclick=async()=>{if(!dubSource)return;try{await api('/api/videos/'+dubSource.id,{method:'DELETE'});dubSource=null;$('dub-source').textContent='Đã xóa video gốc.';$('dub-delete').hidden=true;await refreshDubSources();}catch(e){notify(e.message,true);}};
$('dub-copy-script').onclick=()=>{$('dub-script').value=$('script').value;$('dub-format').value=$('script-format').value;};
function updateDub(job){dubJob=job.id;const working=['queued','running','cancelling'].includes(job.status);taskButtons(working||!!videoTaskId);$('dub-progress').value=job.progress||0;$('dub-percent').textContent=`${job.progress||0}%`;$('dub-generate').disabled=working;$('dub-voice-only').disabled=working;$('dub-stop').hidden=!working;$('dub-stop').disabled=job.status==='cancelling';$('dub-stop').textContent=job.status==='cancelling'?'Đang dừng…':'■ Dừng tạo voice / lồng tiếng / xuất';$('dub-status').textContent=job.error||`${job.status==='done'?'Video đã sẵn sàng':job.phase||'Đang chuẩn bị'} · ${job.progress||0}%`;$('dub-preview').hidden=!job.video_url||job.status!=='done';$('dub-download').hidden=$('dub-preview').hidden;const done=job.status==='done';renderJobAudio(job,$('dub-audio'),$('dub-audio-download'));if(job.video_url&&job.status==='done'){if(!$('dub-preview').src.endsWith(job.video_url))$('dub-preview').src=job.video_url;$('dub-download').href=job.video_url;$('dub-download').download=`voice-studio-${job.id.slice(0,8)}.mp4`;}}
async function submitDub(videoWanted){if(videoWanted&&$('logo-enabled').checked&&(!logoRect||logoVideoId!==dubSource?.id)){notify('Chọn lại vùng logo cho video hiện tại.',true);return;}if(videoWanted&&!dubSource){notify('Tải video vào studio trước.',true);return;}if(!$('dub-voice').value){notify('Chưa có giọng phù hợp với ngôn ngữ đã chọn. Tải giọng quốc tế hoặc cài giọng SAPI Windows.',true);return;}if(!$('dub-script').value.trim()){notify('Nhập lời lồng tiếng trước.',true);return;}const b=$('dub-generate');taskButtons(true);b.disabled=true;$('dub-voice-only').disabled=true;let submitted=false;try{const useEditorCharacters=$('dub-format').value==='srt'&&editorVideoId===dubSource?.id&&$('dub-script').value.trim()===editorSrt(editorCues).trim();const characterSpeech=useEditorCharacters?editorCharacterSpeech(checkedEditorCues()):{};const job=await api('/api/speech',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...characterSpeech,input_format:$('dub-format').value,text:$('dub-script').value,voice_id:$('dub-voice').value,language:$('dub-language').value,format:'wav',speed:Number($('speed').value),quality:$('quality').value,delivery:$('delivery').value,paragraph_pause:Number($('paragraph-pause').value),max_minutes:180,nano_steps:Number($('dub-nano-steps').value),nano_threads:2,nano_parallel:Number($('dub-parallel').value),video_id:videoWanted?dubSource.id:null,video_offset:videoWanted?Number($('dub-offset').value):0,video_mix:$('dub-mix').checked,caption_style:readCaptionStyle(),caption_cues:videoWanted&&$('dub-burn-captions').checked&&editorVideoId===dubSource?.id?editorCues:[],export_resolution:$('editor-resolution').value,export_quality:$('editor-quality').value,logo:null,logos:videoWanted&&$('logo-enabled').checked?selectedLogoRegions():[]})});submitted=true;activeOutputId=job.id;updateDub(job);pollJob(job.id);}catch(e){$('dub-status').textContent=e.message;notify(e.message,true);}finally{if(!submitted){taskButtons(false);b.disabled=false;$('dub-voice-only').disabled=false;}}}
$('dub-generate').onclick=()=>submitDub(true);$('dub-voice-only').onclick=()=>submitDub(false);
$('dub-stop').onclick=async()=>{if(videoTaskId){videoAutoDub=false;await api('/api/video-tasks/'+videoTaskId+'/cancel',{method:'POST'});return;}if(!dubJob)return;try{await api('/api/jobs/'+dubJob+'/cancel',{method:'POST'});}catch(e){notify(e.message,true);}};

function updateDubVoices(){const old=$('dub-voice').value;const source=$('dub-voice-source').value;const options=voices.filter(v=>v.languages.includes($('dub-language').value)&&(source==='all'||(source==='system'?v.engine==='system':v.engine!=='system')));$('dub-voice').replaceChildren(...options.map(v=>{const o=element('option',v.name+(v.native_language?' · '+(config.languages[v.native_language]||({'en':'Mỹ / Anh'}[v.native_language]||v.native_language)):'')+(v.ready===false?' · Chưa tải model':' · Sẵn sàng'));o.value=v.id;return o;}));if(options.some(v=>v.id===old))$('dub-voice').value=old;else{const ready=options.find(v=>v.engine==='system'||(v.engine==='vieneu_nano'?config?.nano_ready:config?.models[v.engine]));if(ready)$('dub-voice').value=ready.id;}updateDubVoiceInfo();}
function updateDubVoiceInfo(){const voice=voices.find(v=>v.id===$('dub-voice').value);$('dub-voice-info').textContent=voice?`${voice.name} · ${voice.description}${voice.ready===false?' · CHƯA TẢI: bấm Tải model cho giọng đang chọn.':' · Sẵn sàng'}`:'Nguồn Windows chưa có giọng cho ngôn ngữ này. Chọn Tất cả giọng hoặc Giọng AI cục bộ, rồi bấm Tải model. Giọng Windows cần cài trong Settings > Time & language > Speech; OneCore không phải giọng SAPI.';if(typeof syncVoiceDownload==='function')syncVoiceDownload('dub');updateHmongVoiceChoices();}
$('dub-language').onchange=updateDubVoices;$('dub-voice-source').onchange=updateDubVoices;$('dub-voice').onchange=()=>{if(isHmongStudio())selectHmongVoice($('dub-voice').value);else updateDubVoiceInfo();};$('voice-source').onchange=updateVoiceOptions;
async function importScript(file,editor,format){
 if(!file)return;
 if(file.size>4*1024**2){notify('Tệp tối đa 4 MB.',true);return;}
 try{
  const text=await readScriptFileText(file);
  if(scriptCharacterCount(text)>scriptCharacterLimit())throw Error('Tối đa '+scriptCharacterLimit().toLocaleString('vi-VN')+' ký tự.');
  const kind=file.name.toLowerCase().endsWith('.srt')||(isHmongStudio()&&hasScriptTimeRanges(text))?'srt':'txt';
  if(kind==='srt')await api('/api/scripts/convert',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,input_format:'srt',output_format:'srt'})});
  $(editor).value=text;$(format).value=kind;
  if(editor==='script'){$('script').oninput();updateSubtitleMode();}
  notify(`Đã nhập ${kind.toUpperCase()}${kind==='srt'?(isHmongStudio()&&editor==='script'&&!$('create-subtitle-timing').checked?' · chỉ đọc lời, bỏ mốc giờ':' và giữ mốc thời gian từng câu'):''}.`);
 }catch(error){notify(error.message,true);}
}
$('import-script').onchange=()=>importScript($('import-script').files[0],'script','script-format');$('dub-import').onchange=()=>importScript($('dub-import').files[0],'dub-script','dub-format');
function downloadText(text,name){const url=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));const link=element('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
async function exportScript(editor,format,extension,jobId){const text=$(editor).value;if(!text.trim()){notify('Chưa có lời đọc.',true);return;}try{if(extension==='srt'&&$(format).value==='srt'&&jobId){const job=await api('/api/jobs/'+jobId);if(job.text.trim()===text.trim()&&job.input_format==='srt'&&job.status==='done'){const response=await fetch(`/api/jobs/${jobId}/script.srt`);if(response.ok){downloadText(await response.text(),'voice-studio.srt');return;}}}if(extension==='srt'&&$(format).value==='txt'){if(!jobId)throw Error('Tạo giọng hoàn tất trước khi xuất SRT để có mốc thời gian thực.');const job=await api('/api/jobs/'+jobId);if(job.text.trim()!==text.trim()||job.input_format==='srt'||job.status!=='done')throw Error('Nội dung đã đổi hoặc tác vụ chưa xong. Tạo lại voice để xuất SRT đúng lời.');if(job.longform){const link=element('a');link.href=jobDownloadUrl(job);link.download=`voice-studio-${job.id.slice(0,8)}.zip`;link.click();notify('SRT riêng cho từng phần nằm trong ZIP cùng âm thanh và TXT.');return;}const response=await fetch(`/api/jobs/${jobId}/script.srt`);if(!response.ok)throw Error('SRT chưa sẵn sàng.');downloadText(await response.text(),'voice-studio.srt');return;}const result=await api('/api/scripts/convert',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,input_format:$(format).value,output_format:extension})});downloadText(result.text,'voice-studio.'+extension);}catch(e){notify(e.message,true);}}
$('export-script-txt').onclick=()=>exportScript('script','script-format','txt',activeOutputId);$('export-script-srt').onclick=()=>exportScript('script','script-format','srt',activeOutputId);$('dub-export-txt').onclick=()=>exportScript('dub-script','dub-format','txt',dubJob);$('dub-export-srt').onclick=()=>exportScript('dub-script','dub-format','srt',dubJob);

function uploadVideo(data){return new Promise((resolve,reject)=>{const xhr=new XMLHttpRequest();xhr.open('POST','/api/videos');xhr.responseType='json';xhr.upload.onprogress=(event)=>{if(event.lengthComputable){const percent=Math.round(100*event.loaded/event.total);$('dub-upload-progress').value=percent;$('dub-source').textContent=percent===100?'Tải lên 100% · Đang kiểm tra video…':`Đang tải video: ${percent}%`;}};xhr.onload=()=>{if(xhr.status>=200&&xhr.status<300)resolve(xhr.response);else reject(Error(xhr.response?.detail||'Không tải được video.'));};xhr.onerror=()=>reject(Error('Mất kết nối khi tải video.'));xhr.send(data);});}
let videoTaskId=null,videoAutoDub=false,logoRect=null,logoImage=null,logoStart=null,logoVideoId=null;
function taskButtons(busy){if(isHmongStudio())for(const id of ['hmong-steps','dub-hmong-steps','delivery','dub-hmong-delivery','hmong-emotion','dub-hmong-emotion','hmong-emotion-strength','dub-hmong-emotion-strength','hmong-auto-rhythm','dub-hmong-auto-rhythm','paragraph-pause','dub-hmong-paragraph-pause'])$(id).disabled=busy;for(const id of ['dub-existing','dub-upload','dub-delete','dub-language','dub-voice','dub-voice-source'])$(id).disabled=busy;for(const id of ['auto-subtitles','translate-existing','auto-dub','logo-export','dub-generate','dub-voice-only','editor-render','editor-dub','editor-recognize','editor-save','editor-add','editor-translate','editor-export-video','editor-export-txt','editor-export-srt','editor-resolution','editor-quality','export-maximum','studio-fast','subtitle-provider','subtitle-target','asr-language','dub-translate-voice','dub-translation-provider','dub-translation-model','dub-burn-captions'])$(id).disabled=busy;$('dub-stop').hidden=!busy;}
async function beginVideoTask(action,existing=false,autoDub=false){if(isHmongStudio()&&action==='subtitles'&&!existing){notify('Chưa có nhận dạng Hmong từ video. Nhập SRT hoặc thêm/sửa lời thủ công trước.',true);return;}if(autoDub&&$('translate-subtitles').checked&&$('subtitle-target').value!==$('dub-language').value&&!$('dub-translate-voice').checked){const message='Ngôn ngữ phụ đề khác ngôn ngữ giọng đọc. Bật Dịch lời lồng tiếng riêng hoặc chọn cùng ngôn ngữ trước.';$('dub-status').textContent=message;notify(message,true);return;}if(videoTaskId){notify('Dừng tác vụ hiện tại trước.',true);return;}if(!dubSource){notify('Chọn video trước.',true);return;}if(action==='logo'&&(!logoRect||logoVideoId!==dubSource.id)){notify('Hiện khung hình và chọn vùng logo của video này trước.',true);return;}if(existing&&$('dub-format').value!=='srt'){notify('Chọn định dạng SRT và nhập phụ đề trước.',true);return;}videoAutoDub=autoDub;taskButtons(true);for(const id of ['dub-preview','dub-download','dub-audio','dub-audio-download'])$(id).hidden=true;$('dub-progress').value=0;$('dub-percent').textContent='0%';try{const task=await api('/api/video-tasks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({video_id:dubSource.id,action,export_resolution:$('editor-resolution').value,export_quality:$('editor-quality').value,source_language:$('asr-language').value,accurate:$('asr-quality').value==='accurate',provider:$('subtitle-provider').value,target_language:$('translate-subtitles').checked?$('subtitle-target').value:'',model:$('subtitle-model').value,srt:existing?$('dub-script').value:'',logo:null,logos:selectedLogoRegions()})});videoTaskId=task.id;await pollVideoTask();}catch(e){$('dub-status').textContent=e.message;notify(e.message,true);videoTaskId=null;taskButtons(false);}}
async function pollVideoTask(){const id=videoTaskId;if(!id)return;try{const task=await api('/api/video-tasks/'+id);$('dub-progress').value=task.progress;$('dub-percent').textContent=task.progress+'%';$('dub-status').textContent=task.error||(task.status==='cancelled'?'Đã dừng':`${task.phase} · ${task.progress}%`);if(['queued','running'].includes(task.status)){setTimeout(pollVideoTask,1000);return;}videoTaskId=null;taskButtons(false);if(task.status==='done'&&task.width)$('dub-status').textContent+=` · ${task.width} × ${task.height}`;if(task.original_srt){$('dub-script').value=task.original_srt;$('dub-format').value='srt';}if(task.status==='done'){if(task.cues&&typeof loadDirectCues==='function'&&task.video_id===dubSource?.id)await loadDirectCues(task.cues);if(task.srt){$('dub-script').value=task.srt;$('dub-format').value='srt';$('dub-offset').value=0;if(videoAutoDub){videoAutoDub=false;await submitDub(true);}}if(task.video_url){$('dub-preview').hidden=false;$('dub-preview').src=task.video_url;$('dub-download').hidden=false;$('dub-download').href=task.video_url;$('dub-download').download='video-logo.mp4';}}videoAutoDub=false;}catch(e){$('dub-status').textContent='Mất kết nối theo dõi, đang thử lại… '+e.message;setTimeout(pollVideoTask,2000);}}
$('auto-subtitles').onclick=()=>beginVideoTask('subtitles');$('translate-existing').onclick=()=>{if(!$('translate-subtitles').checked){notify('Bật Dịch sang ngôn ngữ lời đọc trước.',true);return;}beginVideoTask('subtitles',true);};$('auto-dub').onclick=()=>beginVideoTask('subtitles',false,true);$('logo-export').onclick=()=>beginVideoTask('logo');
function paintLogo(){const canvas=$('logo-canvas'),ctx=canvas.getContext('2d');ctx.drawImage(logoImage,0,0,canvas.width,canvas.height);if(logoRect){ctx.strokeStyle='#ff3355';ctx.lineWidth=3;ctx.strokeRect(logoRect.x,logoRect.y,logoRect.w,logoRect.h);$('logo-region').textContent=`Vùng logo: x=${logoRect.x}, y=${logoRect.y}, rộng=${logoRect.w}, cao=${logoRect.h}`;}}
$('logo-frame').onclick=()=>{if(!dubSource){notify('Chọn video trước.',true);return;}const id=dubSource.id;const image=new Image();image.onload=()=>{if(dubSource?.id!==id)return;logoImage=image;logoVideoId=id;logoRect=null;const c=$('logo-canvas');c.width=image.naturalWidth;c.height=image.naturalHeight;c.hidden=false;paintLogo();};image.onerror=()=>notify('Không lấy được khung hình video.',true);image.src='/api/videos/'+id+'/frame?at='+encodeURIComponent($('editor-video')?.currentTime||Number($('editor-seek')?.value)||0);};
function logoPoint(e){const c=$('logo-canvas'),r=c.getBoundingClientRect();return {x:Math.max(1,Math.min(c.width-2,Math.round((e.clientX-r.left)*c.width/r.width))),y:Math.max(1,Math.min(c.height-2,Math.round((e.clientY-r.top)*c.height/r.height)))};}
$('logo-canvas').onpointerdown=e=>{logoStart=logoPoint(e);$('logo-canvas').setPointerCapture(e.pointerId);};$('logo-canvas').onpointermove=e=>{if(!logoStart)return;const p=logoPoint(e);logoRect={x:Math.min(p.x,logoStart.x),y:Math.min(p.y,logoStart.y),w:Math.abs(p.x-logoStart.x),h:Math.abs(p.y-logoStart.y)};paintLogo();};$('logo-canvas').onpointerup=()=>{logoStart=null;};

$('hmong-test-selected-voice').onclick=async()=>{
 const button=$('hmong-test-selected-voice'),voice=voices.find(v=>v.id===$('voice').value);
 if(!isHmongStudio()||!voice){notify('Chọn giọng Nam, Nữ hoặc giọng cá nhân trước.',true);return;}
 if(voice.ready===false){notify('Model chưa sẵn sàng. Mở tool bằng MO_VOICE_STUDIO_HMONG.bat để hoàn tất tải và kiểm tra model.',true);return;}
 button.disabled=true;
 try{
  const job=await api('/api/speech',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:'Nyob zoo. Ua tsaug rau koj mloog.',voice_id:voice.id,language:'mww',format:'wav',speed:1,delivery:'natural',emotion:'neutral',emotion_strength:0,auto_rhythm:false,paragraph_pause:0,max_minutes:1,hmong_steps:hmongSteps()})});
  $('help-dialog').close();showTab('create');activeOutputId=job.id;setOutput(job);pollJob(job.id);notify('Đang tạo câu kiểm tra bằng '+voice.name+'. Lời bạn đang soạn được giữ nguyên.');
 }catch(error){notify(error.message,true);}finally{button.disabled=false;}
};
