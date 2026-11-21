import {randomUUID} from 'node:crypto';

// Ownership lives in the exact provider document and DOM nodes we edited. A
// marker-looking user draft, a reload or a later human edit is not ownership.
function draftOperation(elementOrOptions,options){
 const node=options?elementOrOptions:null;const {action,token,message,prefix,stage,expected,source}=options||elementOrOptions;
 const key=Symbol.for('muse.studio.owned.drafts');
 const norm=value=>String(value||'').replace(/\r\n?/g,'\n').replace(/\u00a0/g,' ').replace(/\n+/g,'\n').trim();
 const text=node=>norm(node.tagName==='TEXTAREA'?node.value:node.innerText||node.textContent||'');
 let state=globalThis[key];
 if(!state){
  state={nodes:new WeakMap(),records:new Map(),unowned:new WeakSet()};globalThis[key]=state;
  document.addEventListener('input',event=>{
   if(!event.isTrusted)return;const node=event.target;
   if(!(node instanceof Element)||node.closest('[data-message-item]'))return;
   const owned=state.nodes.get(node);
   if(!owned?.writing){state.unowned.add(node);if(owned)owned.dirty=true;}
  },true);
 }
 const current=node?text(node):'',scope=location.origin+location.pathname+location.hash;
 const hasAttachments=()=>Boolean(node.closest('[data-hatch-composer-root],form')?.querySelector('img[src^="blob:"],img[src^="data:"],input[type="file"]')&&(()=>{const root=node.closest('[data-hatch-composer-root],form');return [...root.querySelectorAll('img[src^="blob:"],img[src^="data:"]')].some(image=>!image.closest('[data-message-item]'))||[...root.querySelectorAll('input[type="file"]')].some(input=>input.files?.length)})());
 const own=node?state.nodes.get(node):null;
 if(action==='claim'){
  if(state.unowned.has(node)&&!own?.writing)return {ok:false,reason:'edited'};
  let record=state.records.get(token);
  if(!record){record={token,scope,message:norm(message),prefix:norm(prefix),stage:'typing',nodes:new Set()};state.records.set(token,record);}
  if(record.scope!==scope)return {ok:false,reason:'scope'};
  const entry=own||{records:[],writing:null,dirty:false};
  if(entry.dirty)return {ok:false,reason:'edited'};
  entry.records=[...entry.records.filter(value=>value!==token),token].slice(-8);entry.writing=token;
  state.nodes.set(node,entry);record.nodes.add(node);
  // The framework may later copy the accepted rich-editor message back into
  // its empty fallback textarea. Bind that exact empty mirror now, without
  // suppressing genuine input there or adopting nonempty user content.
  const root=node.closest('[data-hatch-composer-root],form');
  for(const mirror of root?.querySelectorAll('textarea[data-hatch-composer-prehydration-input="true"]')||[]){
   if(mirror===node||text(mirror)||state.unowned.has(mirror))continue;
   const item=state.nodes.get(mirror)||{records:[],writing:null,dirty:false};if(item.dirty)continue;
   item.records=[...item.records.filter(value=>value!==token),token].slice(-8);state.nodes.set(mirror,item);record.nodes.add(mirror);
  }
  for(const [id,old]of state.records){if(state.records.size<=32)break;if(id!==token&&old.stage!=='possible')state.records.delete(id);}return {ok:true};
 }
 if(action==='stage'){
  const record=token?state.records.get(token):own?.records.map(value=>state.records.get(value)).findLast(Boolean);
  if(!record)return {ok:false};record.stage=stage;if(stage==='acknowledged')record.scope=scope;
  for(const target of record.nodes){const item=state.nodes.get(target);if(item?.writing===record.token)item.writing=null;}
  return {ok:true,token:record.token};
 }
 if(action==='enter'){
  const record=own?.records.map(value=>state.records.get(value)).findLast(Boolean);
  if(!record||own.dirty||state.unowned.has(node)||current!==record.message)return {ok:false};record.stage='possible';own.writing=record.token;return {ok:true,token:record.token};
 }
 if(action==='finish-enter'){if(own)own.writing=null;return {ok:true};}
 if(!current&&action!=='legacy-clear'){if(action==='clear'&&node){state.unowned.delete(node);if(own)own.dirty=false;}return {ok:true,empty:true,cleared:false};}
 if(action==='legacy-clear'){
  const actual=source==='textContent'?norm(node.textContent):current;
  if(actual!==norm(expected)||hasAttachments())return {ok:false,reason:'changed-or-attachment'};
 }else{
  if(!own||own.dirty||state.unowned.has(node))return {ok:false,reason:'unowned'};
  const accepted=value=>{const marker=value.message.match(/studio-(?:batch|request)-[a-f0-9-]{36}/i)?.[0];return Boolean(marker&&[...document.querySelectorAll('[data-message-item][data-message-role="user"]')].some(item=>item.getClientRects().length&&item.textContent.includes(marker)));};
  const record=[...own.records].reverse().map(value=>state.records.get(value)).find(value=>value&&(current===value.message||current===value.prefix)&&(value.scope===scope||accepted(value)));
  if(!record)return {ok:false,reason:'unowned'};
  const acknowledged=accepted(record);if(acknowledged)record.scope=scope;
  if(record.stage==='possible'&&!acknowledged)return {ok:false,reason:'uncertain'};
  if(hasAttachments())return {ok:false,reason:'attachment'};
 }
 // Compare and clear in one document task so a changed user draft is never
 // replaced between an ownership check and an asynchronous locator action.
 const targets=[node];
 if(action==='legacy-clear'){
  const root=node.closest('[data-hatch-composer-root],form'),full=norm(expected),first=full[0];
  for(const mirror of root?.querySelectorAll('textarea,[contenteditable="true"],[contenteditable="plaintext-only"]')||[]){
   if(mirror===node)continue;const value=text(mirror);
   if(value===full||norm(mirror.textContent)===full||(mirror.matches('textarea[data-hatch-composer-prehydration-input="true"]')&&value===first))targets.push(mirror);
  }
 }
 for(const target of targets){
  if(target.tagName==='TEXTAREA')Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(target,'');else target.textContent='';
  state.unowned.delete(target);const item=state.nodes.get(target);if(item){item.dirty=false;item.writing=null;}
  target.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'deleteContentBackward'}));
 }
 return {ok:true,cleared:true};
}

export class OwnedDrafts{
 async clear(editor){return editor.evaluate(draftOperation,{action:'clear'});}
 async claim(editor,token,message,prefix){return editor.evaluate(draftOperation,{action:'claim',token,message,prefix});}
 async stage(editor,stage,token){return editor.evaluate(draftOperation,{action:'stage',stage,token});}
 async markFrame(frame,stage,token){return frame.evaluate(draftOperation,{action:'stage',stage,token});}
 async enter(editor){return editor.evaluate(draftOperation,{action:'enter'});}
 async finishEnter(editor){return editor.evaluate(draftOperation,{action:'finish-enter'});}
 async clearLegacy(editor,expected,source){return editor.evaluate(draftOperation,{action:'legacy-clear',expected,source});}
 token(){return randomUUID();}
}

export function batchMessageHeader({marker,count,output,common=''}){return `[${marker}]\nCreate ${count} independent ${output==='video'?'video':'image'} file${count===1?'':'s'} now in this ONE request. Each task below is a separate output; use the available generation tool for every task. ${output==='video'?'Keep the requested duration for EACH video; do not stitch the tasks into one long film.':''} Do not just write a plan or ask whether to start.\nFor each result, put its CLIP label in the same list item or heading as its native attachment or real download link. Preserve the real working URL; never invent file paths or rename files just for tracking. If a task cannot be generated, give its label and concrete reason.\n\n${common?'Apply these instructions to EACH task:\n'+common+'\n\n':''}`;}

export function videoGenerationPrompt(data){
    const referenceInstruction = data.sourceMode === 'image' ? 'Animate the attached image as the starting frame.' : data.referenceImage ? 'Use the attached image as a character reference, not as an unrelated example.' : 'Create the video from the text prompt.';
    const prompt = `Use your video-generation tool to create exactly one new video, not a link to an existing example. Requested model: ${data.modelDisplayName}. Requested duration: ${data.durationSeconds} seconds, aspect ratio: ${data.aspectRatio}, resolution: ${data.resolution}. Start the available video-generation tool now. These are target settings: if an exact model name or parameter is unavailable, use supported generation settings and report the actual settings instead of stopping at a text-only explanation. Do not invent model options, return only a written plan, or ask for confirmation to start this requested generation. If no video generation is available, state the concrete reason. ${referenceInstruction} ${data.characterLock !== false ? 'Preserve the referenced character identity and appearance across scenes.' : 'Follow this scene prompt independently; character consistency is not requested.'}\nScene:\n${data.prompt}`;
    return prompt;
}

export function imageGenerationPrompt(data){
    const longEdge = data.resolution === '4k' ? 3840 : 2560;
    const dimensions = data.aspectRatio === '9:16' ? `${Math.round(longEdge * 9 / 16)}x${longEdge}` : `${longEdge}x${Math.round(longEdge * 9 / 16)}`;
    const useReference = data.characterLock !== false && data.referenceImage;
    const prompt = `Use your image-generation tool to create exactly one new image for this scene. Requested native output: ${data.resolution.toUpperCase()} (${dimensions} pixels), aspect ratio ${data.aspectRatio}. Return the generated image, not a stock image or an old response. Do not claim a higher resolution than the image actually has. ${useReference ? 'Use the attached portrait as a character reference; preserve identity, face and appearance consistently.' : data.characterLock !== false ? 'Follow the character description in this prompt. No portrait is attached; cross-scene identity is not guaranteed without a reference.' : 'Follow this prompt independently. Do not reuse characters or appearance from earlier scenes unless the prompt explicitly requests them.'}\nScene:\n${data.prompt}`;
    return prompt;
}

const canonicalHeads={video:new Set(),image:new Set()};
for(const modelDisplayName of ['Omni 1.1 Flash','Veo 3.1 - Lite','Veo 3.1 - Fast'])for(const durationSeconds of modelDisplayName==='Omni 1.1 Flash'?[4,6,8,10]:[8])for(const aspectRatio of ['16:9','9:16'])for(const resolution of ['360p','720p','1080p','2k','4k'])for(const source of [{sourceMode:'text'},{sourceMode:'text',referenceImage:{}},{sourceMode:'image',referenceImage:{}}])for(const characterLock of [true,false])canonicalHeads.video.add(videoGenerationPrompt({modelDisplayName,durationSeconds,aspectRatio,resolution,...source,characterLock,prompt:''}).split('\nScene:\n')[0]);
for(const resolution of ['2k','4k'])for(const aspectRatio of ['16:9','9:16'])for(const reference of [{characterLock:true,referenceImage:{}},{characterLock:true},{characterLock:false}])canonicalHeads.image.add(imageGenerationPrompt({resolution,aspectRatio,...reference,prompt:''}).split('\nScene:\n')[0]);
const generatedScene=(payload,output)=>{const at=payload.indexOf('\nScene:\n');return at>=0&&canonicalHeads[output].has(payload.slice(0,at))?payload.slice(at+8):null;};

// Explicit recovery for drafts left by older versions without a ledger. Require
// the complete internal envelope and an exact scene, never a short CLIP/prefix.
export function legacyToolDraft(value,prompt,output,{allowPrevious=false}={}){
 const layout=value=>String(value||'').replace(/\r\n?/g,'\n').replace(/\u00a0/g,' ').replace(/\n+/g,'\n');
 const raw=layout(value).trim(),scene=layout(prompt).trim();
 if(!scene||!['image','video'].includes(output))return null;
 const batch=raw.match(/^\[studio-batch-([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})\]\nCreate (\d+) independent (video|image) files? now in this ONE request\./i);
 if(batch&&batch[3]===output){
  const blocks=[...raw.matchAll(/\[BEGIN_CLIP (CLIP_(\d{3})_([a-f0-9]{8})) (MUSE_[a-f0-9]{32})\]\n([\s\S]*?)\n\[END_CLIP \4\]/gi)];
  if(!blocks.length||blocks.length!==Number(batch[2])||blocks.length>6||blocks.some(block=>block[3]!==batch[1].slice(0,8))||new Set(blocks.map(block=>block[4])).size!==blocks.length||new Set(blocks.map(block=>block[1])).size!==blocks.length)return null;
  if(raw.slice(blocks[0].index).replace(/\[BEGIN_CLIP (CLIP_\d{3}_[a-f0-9]{8}) (MUSE_[a-f0-9]{32})\]\n[\s\S]*?\n\[END_CLIP \2\]/gi,'').trim())return null;
  const header=raw.slice(0,blocks[0].index),base=layout(batchMessageHeader({marker:'studio-batch-'+batch[1],count:blocks.length,output}));
  let common='';
  if(header!==base){
    const intro='Apply these instructions to EACH task:\n';
    if(!header.startsWith(base+intro)||!header.endsWith('\n'))return null;
    common=header.slice((base+intro).length,-1);
    if(common.includes('\n')||!canonicalHeads[output].has(common))return null;
  }
  if(header!==layout(batchMessageHeader({marker:'studio-batch-'+batch[1],count:blocks.length,output,common})))return null;
  const scenes=blocks.map(block=>common?block[5].trim():generatedScene(block[5].trim(),output));if(scenes.some(value=>value===null))return null;
  const matched=scenes.includes(scene);
  return matched||allowPrevious?{marker:'studio-batch-'+batch[1],kind:'batch',matchesScene:matched}:null;
 }
 const tag=raw.match(/\[Request marker: (studio-request-[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})\. Do not include this marker in your reply\.\]/i);
 if(!tag)return null;const body=raw.replace(tag[0],'').trim();
 const original=generatedScene(body,output);if(original===null||(!allowPrevious&&original!==scene))return null;
 return {marker:tag[1],kind:'single',matchesScene:original===scene};
}
