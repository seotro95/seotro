// Self-contained function evaluated inside the owned Muse frame. Stable media
// keys, rather than identities of transient React nodes, exclude old history.
export function inspectBatchDOM({marker,rows=[],baseline=[],baselineTexts=[],captureOnly=false,beforeMarker=false,acknowledged=false,allowSingle=false,bindings={},output='video'}){
  const compact=value=>String(value||'').normalize('NFKC').toLowerCase().replace(/[^a-z0-9]/g,'');
  const hash=value=>{let n=2166136261;for(let i=0;i<value.length;i++)n=Math.imul(n^value.charCodeAt(i),16777619);return (n>>>0).toString(16)+':'+value.length};
  const key=value=>{try{const url=new URL(value,location.href);if(url.protocol==='data:')return 'data:'+hash(url.href);url.hash='';for(const name of [...url.searchParams.keys()])if(/^(?:x-amz-.+|signature|expires|key-pair-id|policy|width|height|dpr|quality)$/i.test(name))url.searchParams.delete(name);url.searchParams.sort();return url.href}catch{return value}};
  const native=value=>{try{const url=new URL(value,location.href);return !url.username&&!url.password&&(['attachment:','artifact:'].includes(url.protocol)||(url.protocol==='sandbox:'&&url.pathname.startsWith('/mnt/data/')))}catch{return false}};
  const valid=value=>{try{const url=new URL(value,location.href);return ['https:','data:','blob:'].includes(url.protocol)||(url.protocol==='http:'&&url.hostname==='127.0.0.1')}catch{return false}};
  const all=[...document.querySelectorAll('[data-message-item]')];const users=all.filter(node=>node.getAttribute('data-message-role')==='user');
  const exactAnchor=all.findLastIndex(node=>node.getAttribute('data-message-role')==='user'&&node.textContent.includes(marker||'__missing_marker__'));
  const anchor=exactAnchor>=0?exactAnchor:all.findLastIndex(node=>node.getAttribute('data-message-role')==='user'&&rows.some(row=>compact(node.textContent).includes(compact(row.fileToken))||compact(node.textContent).includes(compact(row.label))));
  const replies=(captureOnly&&beforeMarker?all.slice(0,Math.max(0,anchor)):anchor>=0?all.slice(anchor+1):acknowledged||captureOnly?all:[]).filter(node=>node.getAttribute('data-message-role')==='assistant');
  const seen=new Set(baseline),assets=new Map(),unsupported=[],sources=[];
  const tokenOwners=new Map(rows.map(row=>[compact(row.fileToken),row.fileToken])),labelOwners=new Map(rows.map(row=>[compact(row.label),row.fileToken]));
  const owners=text=>{const raw=String(text||''),tokens=raw.match(/MUSE_[a-f0-9]{32}/gi)||[],labels=raw.match(/CLIP[ _-]*[0-9]{3}[ _-]*[a-f0-9]{8}/gi)||[];const values=tokens.length?tokens:labels,map=tokens.length?tokenOwners:labelOwners;if(values.some(value=>!map.has(compact(value))))return [];return [...new Set(values.map(value=>map.get(compact(value))))];};
  const evidence=node=>[node.textContent,...[...node.attributes].map(item=>item.value),...['aria-labelledby','aria-describedby'].flatMap(name=>(node.getAttribute(name)||'').split(/\s+/).filter(Boolean).map(id=>document.getElementById(id)?.textContent||''))].join(' ');
  const mediaLink=node=>node.matches('a[href]')&&(/\.(?:mp4|webm|mov|png|jpe?g|webp|avif|gif)(?:$|[?#])/i.test(node.href)||Boolean(node.getAttribute('download'))||/^(?:video|image)\//i.test(node.type||'')||/download|tải về/i.test(node.textContent||''));
  const smallScope=node=>node.querySelectorAll(output==='video'?'video':'img').length<=1&&[...node.querySelectorAll('a[href]')].filter(mediaLink).length<=1;
  const elementOwner=element=>{
    let node=element;let own=owners(evidence(element));
    if(own.length===1)return own[0];
    if(mediaLink(element)){const before=element.previousElementSibling;const peer=before?.matches(output==='video'?'video':'img')?before:before?.querySelector(output==='video'?'video':'img');if(peer&&!foreign(peer)&&(!before.querySelectorAll||before.querySelectorAll(output==='video'?'video':'img').length<=1)){const label=elementOwner(peer);if(label)return label}}
    while(node&&node.hasAttribute&&!node.hasAttribute('data-message-item')){
      const inNode=owners(evidence(node));if(inNode.length===1&&smallScope(node))return inNode[0];
      let sibling=node.previousElementSibling;
      for(let n=0;sibling&&n<100;n++,sibling=sibling.previousElementSibling){
        if(sibling.matches('img,video')||sibling.querySelector('img,video')||mediaLink(sibling))break;
        const labels=owners(sibling.textContent);if(labels.length===1)return labels[0];if(labels.length>1)break;
      }
      node=node.parentElement;
    }
    if(node){const labels=owners(evidence(node));if(labels.length===1&&smallScope(node))return labels[0]}
    return null;
  };
  const foreign=element=>{let node=element;while(node&&node.hasAttribute){const value=evidence(node);if(owners(value).length)return false;if(/MUSE_[a-f0-9]{32}|CLIP[ _-]*[0-9]{3}[ _-]*[a-f0-9]{8}/i.test(value))return true;if(node.hasAttribute('data-message-item'))break;node=node.parentElement;}return false;};
  const add=(element,src,kind,rank=1,uncertain=false)=>{if(!src||(!captureOnly&&foreign(element)))return;const id=key(src);const nativeDownload=element.matches('a[href]')&&native(src);if(!valid(src)&&!nativeDownload){unsupported.push({owner:elementOwner(element),kind});return;}if(!captureOnly&&seen.has(id))return;sources.push({key:id,kind,reply:element.closest('[data-message-item]')});const prior=assets.get(id);if(nativeDownload)rank=10;if(nativeDownload)element.dataset.museStudioFileId||=crypto.randomUUID();const value={nativeDownload,nativeId:nativeDownload?element.dataset.museStudioFileId:undefined,key:id,src:new URL(src,location.href).href,kind,rank,uncertain,owner:elementOwner(element)};if(prior?.ambiguous)return;if(prior?.owner&&value.owner&&prior.owner!==value.owner){assets.set(id,{...prior,owner:null,ambiguous:true});return;}if(!prior||rank<prior.rank){value.owner||=prior?.owner||null;assets.set(id,value)}else if(!prior.owner&&value.owner)prior.owner=value.owner};
  for(const reply of replies){
    for(const player of reply.querySelectorAll('video'))add(player,player.currentSrc||player.getAttribute('src')||player.querySelector('source[src]')?.src,'video',2);
    if(output==='image'||captureOnly)for(const image of reply.querySelectorAll('img')){
      const lazy=image.getAttribute('data-src')||image.getAttribute('data-original');
      const loaded=image.complete&&image.naturalWidth>=128&&image.naturalHeight>=128;
      const pending=!image.complete||!image.naturalWidth;
      if(captureOnly||loaded||lazy||pending){const src=lazy||image.currentSrc||image.getAttribute('src');if(src&&!/^(?:data:image\/svg|.*\.svg(?:[?#]|$))/i.test(src))add(image,src,'image',lazy?1:2);}
    }
    for(const link of reply.querySelectorAll('a[href]')){
      const name=[link.href,link.download||'',link.type||''].join(' ');let kind=/\.(mp4|webm|mov)(?:$|[?#\s])|video\//i.test(name)?'video':/\.(png|jpe?g|webp|avif|gif)(?:$|[?#\s])|image\//i.test(name)?'image':null;
      const uncertain=!kind;const direct=owners([link.textContent,link.download,link.href].join(' ')).length===1;const downloadable=Boolean(link.getAttribute('download'))||/download|tải(?:\s+(?:về|video|ảnh|file|tệp))?/i.test(link.textContent||'');
      if(!kind&&(captureOnly||direct||(downloadable&&elementOwner(link))))kind=output;if(kind)add(link,link.href,kind,uncertain?3:0,uncertain);
    }
  }
  const previousTexts=new Set(baselineTexts);
  const completedText=value=>/(?:^|\n)\s*(?:done|completed|finished|here (?:is|are)|đã (?:xong|tạo|hoàn thành)|hoàn tất)(?:\s*[-—–:.]|\s*$)|\bdone\s*[—–:]/i.test(value);
  const tagAtStart=/^[\s*#\[\]({>•\-–—]*(?:\d+[.)]\s*)?(?:CLIP[ _-]*[0-9]{3}[ _-]*[a-f0-9]{8}|MUSE_[a-f0-9]{32})/i;
  const captionInfo=node=>{
    const lines=String(node?.innerText||node?.textContent||'').split(/\n/).map(line=>line.trim());
    const heads=lines.flatMap((line,index)=>tagAtStart.test(line)?[index]:[]);
    const completed=new Set(),declared=new Set(),foreignDeclared=new Set();let foreignCompleted=false,pendingHeading=false;
    for(let n=0;n<heads.length;n++){
      const at=heads[n],segment=lines.slice(at,heads[n+1]??lines.length).join('\n'),finished=completedText(segment);
      const header=lines[at].split(/\bdone\s*[—–:]/i)[0],labels=owners(header);
      const payload=lines.slice(at+1,heads[n+1]??lines.length).find(Boolean)||'';
      const pending=!finished&&/still (?:running|generating|processing)|not ready|waiting|queued|in progress|chưa (?:xong|sẵn sàng)|đang (?:tạo|chạy)/i.test(header+'\n'+payload);
      pendingHeading||=pending;
      if(labels.length===1){if(!pending)declared.add(labels[0]);if(finished)completed.add(labels[0]);}
      else if(!labels.length){const token=header.match(/MUSE_[a-f0-9]{32}|CLIP[ _-]*[0-9]{3}[ _-]*[a-f0-9]{8}/i)?.[0];if(token&&!pending)foreignDeclared.add('foreign:'+compact(token));if(token&&finished)foreignCompleted=true;}
    }
    return {completed,declared,foreignDeclared,foreignCompleted,pendingHeading,boundary:heads.length>0};
  };
  const captions=new Map(all.filter(node=>node.getAttribute('data-message-role')==='assistant').map(node=>[node,captionInfo(node)]));
  const messageKeys=new Map();for(const source of sources)if(source.kind===output){if(!messageKeys.has(source.reply))messageKeys.set(source.reply,new Set());messageKeys.get(source.reply).add(source.key);}
  const cardKeys=node=>[...(messageKeys.get(node)||[])];
  const linked=new Set();
  if(!captureOnly)for(const [owner,id]of Object.entries(bindings)){
    const asset=assets.get(id);if(!asset||asset.ambiguous||!rows.some(row=>row.fileToken===owner))continue;
    if(asset.owner&&asset.owner!==owner){asset.owner=null;asset.ambiguous=true;continue;}
    asset.owner=owner;asset.attribution='validated-binding';linked.add(id);
  }
  // Explicit labels can precede or follow a native card. Build candidates from
  // the two neighbouring sections, bounded by another label or a user turn.
  // Only a one-to-one assignment forced in every maximum matching is accepted.
  const candidates=new Map();
  const rawForeignMedia=node=>[...node.querySelectorAll('video,img,a[href]')].some(element=>foreign(element));
  if(!captureOnly)for(const reply of replies){
    if(previousTexts.has(hash(reply.textContent||'')))continue;
    const info=captions.get(reply),labels=[...(info?.declared||[]),...(info?.foreignDeclared||[])];
    if(labels.length!==1||cardKeys(reply).length)continue;
    const owner=labels[0];if([...assets.values()].some(asset=>asset.owner===owner))continue;
    const index=all.indexOf(reply);
    for(const direction of [-1,1]){
      const ids=new Set();
      for(let i=index+direction;i>anchor&&i<all.length;i+=direction){
        const node=all[i];if(node.getAttribute('data-message-role')==='user'||captions.get(node)?.boundary||rawForeignMedia(node))break;
        for(const id of cardKeys(node))ids.add(id);
      }
      if(ids.size!==1)continue;
      const id=[...ids][0],asset=assets.get(id);if(!asset||asset.ambiguous||asset.owner)continue;
      if(!candidates.has(owner))candidates.set(owner,new Set());candidates.get(owner).add(id);
    }
  }
  const maximum=(skipOwner,skipId)=>{
    const occupied=new Map();
    const augment=(owner,visited)=>{for(const id of candidates.get(owner)||[]){if(owner===skipOwner&&id===skipId||visited.has(id))continue;visited.add(id);const previous=occupied.get(id);if(!previous||augment(previous,visited)){occupied.set(id,owner);return true;}}return false;};
    for(const owner of candidates.keys())augment(owner,new Set());return occupied;
  };
  const assignment=maximum();
  for(const [id,owner]of assignment){
    if(maximum(owner,id).size===assignment.size)continue;
    const asset=assets.get(id);if(owner.startsWith('foreign:')){assets.delete(id);continue;}
    asset.owner=owner;asset.attribution='unique-label-scope';linked.add(id);
  }
  const captionLinked=linked.size;
  const media=[...assets.values()];if(captureOnly)return {keys:media.map(item=>item.key),texts:replies.map(node=>hash(node.textContent||''))};
  const matches={};for(const row of rows){const owned=media.filter(item=>item.kind===output&&item.owner===row.fileToken).sort((a,b)=>a.rank-b.rank);if(owned[0])matches[row.fileToken]=owned[0]}
  const unclaimed=media.filter(item=>item.kind===output&&!item.owner);
  if(allowSingle&&rows.length===1&&!matches[rows[0].fileToken]&&unclaimed.length===1)matches[rows[0].fileToken]=unclaimed[0];
  const freshReplies=replies.filter(node=>!previousTexts.has(hash(node.textContent||''))&&(!foreign(node)||captions.get(node)?.declared.size));
  const text=freshReplies.map(node=>node.innerText).join('\n\n').trim();
  const rowTexts={},general=[];
  for(const reply of freshReplies){const blocks=[...reply.querySelectorAll('p,li,h1,h2,h3,h4,h5,h6,div')].filter(node=>!node.querySelector('p,li,h1,h2,h3,h4,h5,h6,div'));for(const block of blocks.length?blocks:[reply]){const value=block.innerText?.trim();if(!value)continue;const owner=elementOwner(block);if(owner)rowTexts[owner]=[rowTexts[owner],value].filter(Boolean).join('\n\n');else general.push(value)}}
  const rowErrors={};for(const reply of freshReplies)for(const notice of reply.querySelectorAll('[data-testid="assistant-response-error-notice"]')){const owner=elementOwner(notice);if(owner)rowErrors[owner]=notice.innerText}
  const completedRows=new Set([...freshReplies.flatMap(node=>[...(captions.get(node)?.completed||[])]),...media.map(item=>item.owner).filter(Boolean)]).size;
  const sceneId=token=>Number(rows.find(row=>row.fileToken===token)?.label?.match(/CLIP[ _-]*(\d{3})/i)?.[1])||null;
  const replyLayout=all.slice(Math.max(anchor+1,all.length-24)).map((node,index)=>({index:Math.max(anchor+1,all.length-24)+index,role:node.getAttribute('data-message-role')||'unknown',mediaSources:cardKeys(node).length,completedScenes:[...(captions.get(node)?.completed||[])].map(sceneId).filter(Boolean),headingScenes:[...(captions.get(node)?.declared||[])].map(sceneId).filter(Boolean),pendingHeading:Boolean(captions.get(node)?.pendingHeading),foreignCompletion:Boolean(captions.get(node)?.foreignCompleted),progress:/still (?:running|processing)|as (?:soon as|it finishes)|I[’']ll send|đang (?:tạo|chạy)|còn .*đang/i.test(node.innerText||'')}));
  return {anchored:anchor>=0,text,rowTexts,rowErrors,generalText:general.join('\n\n'),replyCount:freshReplies.length,streaming:Boolean(document.querySelector('[data-testid="hatch-composer-stop-button"]')?.getClientRects().length),matches,media:media.filter(item=>item.kind===output),unclaimed:unclaimed.length,captionLinked,completedRows,replyLayout,unsupported:unsupported.filter(item=>item.kind===output),otherUserAfterAnchor:anchor>=0&&all.slice(anchor+1).some(node=>node.getAttribute('data-message-role')==='user')};
}
