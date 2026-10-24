/* All selection coordinates are source pixels, shared with the renderer. */
let directDrawing=false,directStart=null,directDraft=null;
const directCanvas=$('video-logo-overlay'),directVideo=$('editor-video');
function directFrame(){
 const w=directVideo.videoWidth,h=directVideo.videoHeight;if(!w||!h)return null;
 const box=directVideo.getBoundingClientRect(),scale=Math.min(box.width/w,box.height/h);
 return {w,h,width:w*scale,height:h*scale,left:(box.width-w*scale)/2,top:(box.height-h*scale)/2};
}
function paintDirectLogos(){
 const f=directFrame();if(!f)return;directCanvas.width=f.w;directCanvas.height=f.h;
 Object.assign(directCanvas.style,{width:f.width+'px',height:f.height+'px',left:f.left+'px',top:f.top+'px'});
 const ctx=directCanvas.getContext('2d');
 for(const [i,r]of [...selectedLogoRegions(),...(directDraft?[directDraft]:[])].entries()){
  if(r.mode==='color'){ctx.fillStyle=r.color;ctx.fillRect(r.x,r.y,r.w,r.h);}
  if(directDrawing||r.mode!=='color'){ctx.strokeStyle='#a78bfa';ctx.lineWidth=Math.max(2,f.w/500);ctx.strokeRect(r.x,r.y,r.w,r.h);ctx.fillStyle='#fff';ctx.font=Math.max(16,f.h/30)+'px Arial';ctx.fillText(String(i+1),r.x+4,r.y+24);}
 }
}
const syncDirectOriginal=syncLogoSelection;syncLogoSelection=function(){syncDirectOriginal();paintDirectLogos();};
function setDirectDrawing(value){directDrawing=value;directStart=null;directDraft=null;directCanvas.style.pointerEvents=value?'auto':'none';$('video-logo-done').hidden=!value;$('video-logo-draw').textContent=value?'Kéo chuột trên video để thêm vùng':'Khoanh / che logo ngay trên video';paintDirectLogos();}
$('video-logo-draw').onclick=()=>{if(!dubSource||!directVideo.videoWidth){notify('Tải video và chờ hiện hình trước.',true);return;}if(logoVideoId!==dubSource.id){logoRegions=[];logoSelected=-1;}logoVideoId=dubSource.id;directVideo.pause();setDirectDrawing(true);$('video-logo-status').textContent='Kéo để khoanh vùng. Có thể khoanh tối đa 20 ô; chọn màu / nội suy bên dưới. Bấm Xong để xem video.';};
$('video-logo-done').onclick=()=>setDirectDrawing(false);
function directPoint(e){const r=directCanvas.getBoundingClientRect(),m=$('logo-mode').value==='color'?0:1;return{x:Math.max(m,Math.min(directCanvas.width-m-1,Math.round((e.clientX-r.left)*directCanvas.width/r.width))),y:Math.max(m,Math.min(directCanvas.height-m-1,Math.round((e.clientY-r.top)*directCanvas.height/r.height)))};}
directCanvas.onpointerdown=e=>{if(logoRegions.length>=20){notify('Tối đa 20 vùng.',true);return;}directStart=directPoint(e);directCanvas.setPointerCapture(e.pointerId);};
directCanvas.onpointermove=e=>{if(!directStart)return;const p=directPoint(e);directDraft={x:Math.min(p.x,directStart.x),y:Math.min(p.y,directStart.y),w:Math.abs(p.x-directStart.x),h:Math.abs(p.y-directStart.y),mode:$('logo-mode').value,color:$('logo-color').value};paintDirectLogos();};
directCanvas.onpointerup=()=>{if(directDraft&&directDraft.w>=2&&directDraft.h>=2){logoRegions.push(directDraft);logoSelected=logoRegions.length-1;}directStart=null;directDraft=null;syncLogoSelection();if(editorVideoId)markEditorDirty();};
directCanvas.onpointercancel=()=>{directStart=null;directDraft=null;paintDirectLogos();};
directVideo.addEventListener('loadedmetadata',()=>{setDirectDrawing(false);paintDirectLogos();});new ResizeObserver(paintDirectLogos).observe(directVideo);
$('caption-preset').onchange=()=>{const preset=$('caption-preset').value;if(preset==='custom')return;setCaptionStyle({...readCaptionStyle(),font:'Arial',color:preset==='yellow'?'#ffff00':'#ffffff',bold:preset!=='cinema',italic:false,outline_color:'#000000',outline:2,background:preset==='panel',background_color:'#000000'});if(editorVideoId)markEditorDirty();};
// Fast text generation is separate from reading speed; keep the chosen speaker.
const initializeFastText=setInterval(()=>{if(!config)return;clearInterval(initializeFastText);$('nano-steps').value='4';$('paragraph-pause').value='0';$('nano-parallel').value=(config.cpu_cores>=4&&config.available_ram_gb>=3)?'2':'1';},100);
$('subtitle-target').addEventListener('change',()=>{$('translate-subtitles').checked=true;$('workspace-connection').open=true;workspaceMessage('Đã chọn ngôn ngữ phụ đề đích. Bấm Tạo phụ đề riêng hoặc Tạo / dịch phụ đề; chỉ dịch khi bạn bấm nút.');});
const editorOriginalProofBusy=proofBusy;proofBusy=function(busy){editorOriginalProofBusy(busy);editorSetBusy(busy,'proof');};
const editorOriginalCreateProof=createProof;createProof=async function(...args){
 if(editorBusy){notify('Đợi hoặc dừng tác vụ hiện tại trước.',true);return;}
 editorSetBusy(true,'proof-submit');try{return await editorOriginalCreateProof(...args);}finally{editorSetBusy(false,'proof-submit');}
};
