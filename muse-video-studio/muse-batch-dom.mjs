// Self-contained function evaluated inside the owned Muse frame. Stable media
// keys, rather than identities of transient React nodes, exclude old history.
export function inspectBatchDOM({marker,rows=[],baseline=[],baselineTexts=[],captureOnly=false,beforeMarker=false,acknowledged=false,allowSingle=false,output='video'}){
  const compact=value=>String(value||'').normalize('NFKC').toLowerCase().replace(/[^a-z0-9]/g,'');
  const hash=value=>{let n=2166136261;for(let i=0;i<value.length;i++)n=Math.imul(n^value.charCodeAt(i),16777619);return (n>>>0).toString(16)+':'+value.length};
  const key=value=>{try{const url=new URL(value,location.href);if(url.protocol==='data:')return 'data:'+hash(url.href);url.hash='';for(const name of [...url.searchParams.keys()])if(/^(?:x-amz-.+|signature|expires|key-pair-id|policy|width|height|dpr|quality)$/i.test(name))url.searchParams.delete(name);url.searchParams.sort();return url.href}catch{return value}};
  const valid=value=>{try{const url=new URL(value,location.href);return ['https:','data:','blob:'].includes(url.protocol)||(url.protocol==='http:'&&url.hostname==='127.0.0.1')}catch{return false}};
  const all=[...document.querySelectorAll('[data-message-item]')];const users=all.filter(node=>node.getAttribute('data-message-role')==='user');
  const exactAnchor=all.findLastIndex(node=>node.getAttribute('data-message-role')==='user'&&node.textContent.includes(marker||'__missing_marker__'));
  const anchor=exactAnchor>=0?exactAnchor:all.findLastIndex(node=>node.getAttribute('data-message-role')==='user'&&rows.some(row=>compact(node.textContent).includes(compact(row.fileToken))||compact(node.textContent).includes(compact(row.label))));
  const replies=(captureOnly&&beforeMarker?all.slice(0,Math.max(0,anchor)):anchor>=0?all.slice(anchor+1):acknowledged||captureOnly?all:[]).filter(node=>node.getAttribute('data-message-role')==='assistant');
  const seen=new Set(baseline),assets=new Map(),unsupported=[],sources=[];
  const owners=text=>{const value=compact(text),tokens=String(text||'').match(/MUSE_[a-f0-9]{32}/gi)||[];const exact=rows.filter(row=>value.includes(compact(row.fileToken))).map(row=>row.fileToken);if(tokens.length)return tokens.some(token=>!rows.some(row=>compact(row.fileToken)===compact(token)))?[]:exact;const labels=String(text||'').match(/CLIP[ _-]*[0-9]{3}[ _-]*[a-f0-9]{8}/gi)||[];if(labels.some(label=>!rows.some(row=>compact(row.label)===compact(label))))return [];return rows.filter(row=>value.includes(compact(row.label))).map(row=>row.fileToken)};
  const mediaLink=node=>node.matches('a[href]')&&(/\.(?:mp4|webm|mov|png|jpe?g|webp|avif|gif)(?:$|[?#])/i.test(node.href)||Boolean(node.getAttribute('download'))||/^(?:video|image)\//i.test(node.type||'')||/download|tải về/i.test(node.textContent||''));
  const smallScope=node=>node.querySelectorAll(output==='video'?'video':'img').length<=1&&[...node.querySelectorAll('a[href]')].filter(mediaLink).length<=1;
  const elementOwner=element=>{
    let node=element;let own=owners([element.textContent,element.getAttribute('alt'),element.getAttribute('aria-label'),element.getAttribute('download'),element.getAttribute('src'),element.getAttribute('href')].filter(Boolean).join(' '));
    if(own.length===1)return own[0];
    if(mediaLink(element)){const before=element.previousElementSibling;const peer=before?.matches(output==='video'?'video':'img')?before:before?.querySelector(output==='video'?'video':'img');if(peer&&!foreign(peer)&&(!before.querySelectorAll||before.querySelectorAll(output==='video'?'video':'img').length<=1)){const label=elementOwner(peer);if(label)return label}}
    while(node&&node.hasAttribute&&!node.hasAttribute('data-message-item')){
      const inNode=owners(node.textContent);if(inNode.length===1&&smallScope(node))return inNode[0];
      let sibling=node.previousElementSibling;
      for(let n=0;sibling&&n<100;n++,sibling=sibling.previousElementSibling){
        if(sibling.matches('img,video')||sibling.querySelector('img,video')||mediaLink(sibling))break;
        const labels=owners(sibling.textContent);if(labels.length===1)return labels[0];if(labels.length>1)break;
      }
      node=node.parentElement;
    }
    if(node){const labels=owners(node.textContent);if(labels.length===1&&smallScope(node))return labels[0]}
    return null;
  };
  const foreign=element=>{let node=element;while(node&&node.hasAttribute){const value=[node.textContent,node.getAttribute('alt'),node.getAttribute('aria-label'),node.getAttribute('download'),node.getAttribute('src'),node.getAttribute('href')].filter(Boolean).join(' ');if(owners(value).length)return false;if(/MUSE_[a-f0-9]{32}|CLIP[ _-]*[0-9]{3}[ _-]*[a-f0-9]{8}/i.test(value))return true;if(node.hasAttribute('data-message-item'))break;node=node.parentElement;}return false;};
  const add=(element,src,kind,rank=1,uncertain=false)=>{if(!src||(!captureOnly&&foreign(element)))return;const id=key(src);if(!valid(src)){unsupported.push({owner:elementOwner(element),kind});return;}if(!captureOnly&&seen.has(id))return;sources.push({key:id,kind,reply:element.closest('[data-message-item]')});const prior=assets.get(id);const value={key:id,src:new URL(src,location.href).href,kind,rank,uncertain,owner:elementOwner(element)};if(prior?.ambiguous)return;if(prior?.owner&&value.owner&&prior.owner!==value.owner){assets.set(id,{...prior,owner:null,ambiguous:true});return;}if(!prior||rank<prior.rank){value.owner||=prior?.owner||null;assets.set(id,value)}else if(!prior.owner&&value.owner)prior.owner=value.owner};
  for(const reply of replies){
    for(const player of reply.querySelectorAll('video'))add(player,player.currentSrc||player.getAttribute('src')||player.querySelector('source[src]')?.src,'video',2);
    if(output==='image'||captureOnly)for(const image of reply.querySelectorAll('img'))if(captureOnly||(image.complete&&image.naturalWidth>=128&&image.naturalHeight>=128))add(image,image.currentSrc||image.src,'image',2);
    for(const link of reply.querySelectorAll('a[href]')){
      const name=[link.href,link.download||'',link.type||''].join(' ');let kind=/\.(mp4|webm|mov)(?:$|[?#\s])|video\//i.test(name)?'video':/\.(png|jpe?g|webp|avif|gif)(?:$|[?#\s])|image\//i.test(name)?'image':null;
      const uncertain=!kind;const direct=owners([link.textContent,link.download,link.href].join(' ')).length===1;const downloadable=Boolean(link.getAttribute('download'))||/download|tải(?:\s+(?:về|video|ảnh|file|tệp))?/i.test(link.textContent||'');
      if(!kind&&(captureOnly||direct||(downloadable&&elementOwner(link))))kind=output;if(kind)add(link,link.href,kind,uncertain?3:0,uncertain);
    }
  }
  const previousTexts=new Set(baselineTexts);
  const completedText=value=>/(?:^|\n)\s*(?:done|completed|finished|here (?:is|are)|đã (?:xong|tạo|hoàn thành)|hoàn tất)(?:\s*[-—–:.]|\s*$)|\bdone\s*[—–:]/i.test(value);
  const tagAtStart=/^[\s*#\[({]*?(?:CLIP[ _-]*[0-9]{3}[ _-]*[a-f0-9]{8}|MUSE_[a-f0-9]{32})/i;
  const captionInfo=node=>{
    const lines=String(node?.innerText||node?.textContent||'').split(/\n/).map(line=>line.trim());
    const heads=lines.flatMap((line,index)=>tagAtStart.test(line)?[index]:[]);
    const completed=new Set();let foreignCompleted=false;
    for(let n=0;n<heads.length;n++){
      const at=heads[n],segment=lines.slice(at,heads[n+1]??lines.length).join('\n');
      if(!completedText(segment))continue;
      const header=lines[at].split(/\bdone\s*[—–:]/i)[0],labels=owners(header);
      if(labels.length===1)completed.add(labels[0]);
      else if(!labels.length&&/MUSE_[a-f0-9]{32}|CLIP[ _-]*[0-9]{3}[ _-]*[a-f0-9]{8}/i.test(header))foreignCompleted=true;
    }
    return {completed,foreignCompleted,boundary:completed.size>0||foreignCompleted};
  };
  const captions=new Map(all.filter(node=>node.getAttribute('data-message-role')==='assistant').map(node=>[node,captionInfo(node)]));
  const messageKeys=new Map();for(const source of sources)if(source.kind===output){if(!messageKeys.has(source.reply))messageKeys.set(source.reply,new Set());messageKeys.get(source.reply).add(source.key);}
  const cardKeys=node=>[...(messageKeys.get(node)||[])];
  const linked=new Set();
  // One result can span several native messages: media, progress notices, then
  // its labelled completion. Search the whole segment between completed tasks
  // and user turns. A segment with multiple unlabelled files stays ambiguous.
  if(!captureOnly)for(const reply of replies){
    if(previousTexts.has(hash(reply.textContent||'')))continue;
    const info=captions.get(reply);if(!info?.boundary||info.completed.size>1)continue;
    if(cardKeys(reply).length)continue; // In-message attribution already handled.
    const index=all.indexOf(reply),ids=new Set();
    for(let i=index-1;i>anchor;i--){
      const node=all[i];if(node.getAttribute('data-message-role')==='user'||captions.get(node)?.boundary)break;
      for(const id of cardKeys(node))ids.add(id);
    }
    if(ids.size!==1)continue;
    const id=[...ids][0],asset=assets.get(id);if(!asset||asset.ambiguous)continue;
    if(info.foreignCompleted&&!info.completed.size){if(!asset.owner)assets.delete(id);continue;}
    const owner=[...info.completed][0];if(!owner)continue;
    let conflictingCaption=false;
    for(let i=index+1;i<all.length;i++){
      const node=all[i];if(node.getAttribute('data-message-role')==='user'||cardKeys(node).length)break;
      const next=captions.get(node);if(next?.boundary){conflictingCaption=next.foreignCompleted||next.completed.size!==1||!next.completed.has(owner);break;}
    }
    if(conflictingCaption)continue;
    if(asset.owner&&asset.owner!==owner){asset.owner=null;asset.ambiguous=true;continue;}
    asset.owner=owner;asset.attribution='caption-segment';linked.add(id);
  }
  const captionLinked=linked.size;
  const media=[...assets.values()];if(captureOnly)return {keys:media.map(item=>item.key),texts:replies.map(node=>hash(node.textContent||''))};
  const matches={};for(const row of rows){const owned=media.filter(item=>item.kind===output&&item.owner===row.fileToken).sort((a,b)=>a.rank-b.rank);if(owned[0])matches[row.fileToken]=owned[0]}
  const unclaimed=media.filter(item=>item.kind===output&&!item.owner);
  if(allowSingle&&rows.length===1&&!matches[rows[0].fileToken]&&unclaimed.length===1)matches[rows[0].fileToken]=unclaimed[0];
  const freshReplies=replies.filter(node=>!previousTexts.has(hash(node.textContent||''))&&(!foreign(node)||captions.get(node)?.completed.size));
  const text=freshReplies.map(node=>node.innerText).join('\n\n').trim();
  const rowTexts={},general=[];
  for(const reply of freshReplies){const blocks=[...reply.querySelectorAll('p,li,h1,h2,h3,h4,h5,h6,div')].filter(node=>!node.querySelector('p,li,h1,h2,h3,h4,h5,h6,div'));for(const block of blocks.length?blocks:[reply]){const value=block.innerText?.trim();if(!value)continue;const owner=elementOwner(block);if(owner)rowTexts[owner]=value;else general.push(value)}}
  const rowErrors={};for(const reply of freshReplies)for(const notice of reply.querySelectorAll('[data-testid="assistant-response-error-notice"]')){const owner=elementOwner(notice);if(owner)rowErrors[owner]=notice.innerText}
  const completedRows=new Set(freshReplies.flatMap(node=>[...(captions.get(node)?.completed||[])])).size;
  const sceneId=token=>Number(rows.find(row=>row.fileToken===token)?.label?.match(/CLIP[ _-]*(\d{3})/i)?.[1])||null;
  const replyLayout=all.slice(Math.max(anchor+1,all.length-24)).map((node,index)=>({index:Math.max(anchor+1,all.length-24)+index,role:node.getAttribute('data-message-role')||'unknown',mediaSources:cardKeys(node).length,completedScenes:[...(captions.get(node)?.completed||[])].map(sceneId).filter(Boolean),foreignCompletion:Boolean(captions.get(node)?.foreignCompleted),progress:/still (?:running|processing)|as (?:soon as|it finishes)|I[’']ll send|đang (?:tạo|chạy)|còn .*đang/i.test(node.innerText||'')}));
  return {anchored:anchor>=0,text,rowTexts,rowErrors,generalText:general.join('\n\n'),replyCount:freshReplies.length,streaming:Boolean(document.querySelector('[data-testid="hatch-composer-stop-button"]')?.getClientRects().length),matches,media:media.filter(item=>item.kind===output),unclaimed:unclaimed.length,captionLinked,completedRows,replyLayout,unsupported:unsupported.filter(item=>item.kind===output),otherUserAfterAnchor:anchor>=0&&all.slice(anchor+1).some(node=>node.getAttribute('data-message-role')==='user')};
}
