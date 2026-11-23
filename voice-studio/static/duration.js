/* Durations use clocks or decimal minutes; never estimate from word counts. */
function parseTargetDuration(value) {
  const text=String(value).trim().replace(',', '.');
  if(!text)return null;
  let seconds;
  if(/^\d+(?:\.\d+)?$/.test(text)){
    seconds=Number(text)*60;
  }else{
    const fields=text.split(':');
    if(fields.length<2||fields.length>3||!fields.every((part,i)=>i===fields.length-1?/^[0-5]\d(?:\.\d{1,3})?$/.test(part):/^\d+$/.test(part)))
      throw Error('Nhập thời lượng dạng 10:00, 01:10:00 hoặc số phút, ví dụ 10,5.');
    if(fields.length===3&&Number(fields[1])>=60)throw Error('Phần phút trong giờ:phút:giây phải nhỏ hơn 60.');
    seconds=fields.map(Number).reduce((total,part)=>total*60+part,0);
  }
  seconds=Math.round(seconds*1000)/1000;
  if(!Number.isFinite(seconds)||seconds<=0||seconds>10800)
    throw Error('Thời lượng đích phải lớn hơn 0 và không quá 180 phút.');
  return seconds;
}
function readTargetDuration(id, format='txt') {
  return format==='srt'?null:parseTargetDuration(document.getElementById(id)?.value||'');
}
function durationInputValue(seconds) {
  const ms=Math.round(seconds*1000);
  return String(Math.floor(ms/60000)).padStart(2,'0')+':'+String(Math.floor(ms/1000)%60).padStart(2,'0')+(ms%1000?'.'+String(ms%1000).padStart(3,'0'):'');
}
function setupDurationInputs(){
  for(const [formatId,targetId]of [['script-format','target-duration'],['dub-format','dub-target-duration'],['workspace-free-input-format','workspace-free-target-duration']]){
    const select=document.getElementById(formatId),input=document.getElementById(targetId);
    if(!select||!input)continue;
    const update=()=>{input.disabled=select.value==='srt';};
    select.addEventListener('change',update);update();
  }
}
if(typeof document!=='undefined')document.addEventListener('DOMContentLoaded',setupDurationInputs);
if(typeof module!=='undefined')module.exports={parseTargetDuration,readTargetDuration,durationInputValue};
