// Activate only an existing media download control in the owned Muse frame. This does
// not turn sandbox paths into local paths, guess an API, or ask for generation.
export function nativeAttachmentURL(value){
  try{const url=new URL(value);return !url.username&&!url.password&&(['attachment:','artifact:'].includes(url.protocol)||(url.protocol==='sandbox:'&&Boolean(url.pathname||url.hostname)))}catch{return false}
}
const imageCaptureGuards=new WeakMap();
const uncertainImageCapture=()=>Error('MEDIA_ATTACHMENT_UNCERTAIN: Lượt tải ảnh trước chưa xác nhận xong; chưa bấm tải tệp tiếp để tránh ghép nhầm cảnh. Bấm Tải lại Muse, rồi Nhận lại từ Muse; không cần tạo lại ảnh.');
const discardDownload=async item=>{await item.cancel().catch(()=>{});await item.delete().catch(()=>{})};
const documentEpoch=page=>page.evaluate(()=>{const key=Symbol.for('muse.studio.attachment.document');return globalThis[key]||=crypto.randomUUID()});
async function captureGuard(page,create){
  let guard=imageCaptureGuards.get(page);if(!guard&&!create)return null;
  const epoch=await documentEpoch(page);
  if(!guard){
    guard={epoch,blocked:false,changed:new Set()};imageCaptureGuards.set(page,guard);
    guard.refresh=async()=>{const next=await documentEpoch(page);if(next!==guard.epoch){guard.epoch=next;guard.blocked=false;for(const changed of [...guard.changed])changed()}return next};
    const download=item=>{if(guard.blocked)void guard.refresh().then(()=>{if(guard.blocked)return discardDownload(item)}).catch(()=>discardDownload(item)).catch(()=>{})};
    const navigated=frame=>{if(frame===page.mainFrame())void guard.refresh().catch(()=>{})};
    page.on('download',download);page.on('framenavigated',navigated);
    page.once('close',()=>{page.off('download',download);page.off('framenavigated',navigated);imageCaptureGuards.delete(page)});
  }else if(epoch!==guard.epoch){guard.epoch=epoch;guard.blocked=false;for(const changed of [...guard.changed])changed()}
  if(guard.blocked)throw uncertainImageCapture();return guard;
}
export async function clickNativeAttachment(frame,media,signal,{onTrigger=()=>{}}={}){
  signal.throwIfAborted();if(!media.nativeControl&&!nativeAttachmentURL(media.src))throw Error('MEDIA_URL_UNSUPPORTED');
  const action=await frame.evaluate(({src,nativeId,nativeButton,nativeControl,kind})=>{
    const matches=[...document.querySelectorAll(nativeButton?'button,[role="button"]':'a[href]')].filter(node=>nativeButton?node.dataset.museStudioFileId===nativeId:(()=>{try{return new URL(node.getAttribute('href'),location.href).href===src}catch{return false}})());
    const node=matches.find(item=>nativeId&&item.dataset.museStudioFileId===nativeId)||(matches.length===1?matches[0]:null);
    if(!node)return null;
    if(!nativeButton){const url=new URL(node.getAttribute('href'),location.href);if(url.username||url.password||/^(?:javascript|vbscript|mailto|tel|sms|intent|shell|ms-[a-z-]+):$/i.test(url.protocol))return null;}
    else{const name=[node.getAttribute('aria-label'),node.getAttribute('title'),node.innerText].join(' ');if(!/\bdownload\b|\bsave (?:image|video|file)\b|tải (?:xuống|về|ảnh|video|tệp|file)/i.test(name)||/\b(?:all|zip|generate|create)\b|tất cả|tạo (?:ảnh|video)/i.test(name))return null;}
    node.dataset.museStudioFileId||=crypto.randomUUID();
    // A same-origin image link can download through browser navigation without
    // an onclick handler. Mark only that existing, owned link as a download so
    // the browser sends its original URL and leaves the chat in place. Remote
    // origins, virtual/file references and the working video path are unchanged.
    const url=!nativeButton?new URL(node.getAttribute('href'),location.href):null;
    const temporaryDownload=kind==='image'&&nativeControl&&!nativeButton&&!node.hasAttribute('download')&&url.origin===location.origin&&/^https?:$/.test(url.protocol);
    if(temporaryDownload)node.setAttribute('download','');
    // Run the site's existing download handler, then suppress only the default
    // link navigation. Virtual/file URIs are never fetched or read on the host.
    const browserDownload=!nativeButton&&node.hasAttribute('download')&&/^(?:https?:|blob:|filesystem:|data:(?:image|video)\/)/i.test(node.href||node.getAttribute('href')||'');
    const protect=event=>{if(event.target===node||node.contains(event.target)){if(!browserDownload)event.preventDefault();cleanup()}};
    const cleanup=()=>{clearTimeout(timer);window.removeEventListener('click',protect)};
    const timer=setTimeout(cleanup,6000);window.addEventListener('click',protect);
    return {id:node.dataset.museStudioFileId,temporaryDownload};
  },{src:media.src,nativeId:media.nativeId,nativeButton:Boolean(media.nativeButton),nativeControl:Boolean(media.nativeControl),kind:media.kind});
  if(!action)throw Error('MEDIA_ATTACHMENT_LINK_CHANGED: Chưa xác định được đúng liên kết tệp Muse.');
  const {id,temporaryDownload}=action;
  const link=frame.locator(`[data-muse-studio-file-id="${id}"]`);
  // A trusted browser click preserves the user gesture required by some
  // service download handlers. It still targets only the matched control.
  const previousType=await link.evaluate(node=>{const type=node.getAttribute('type');if(node.tagName==='BUTTON')node.setAttribute('type','button');return type});
  try{signal.throwIfAborted();if(onTrigger()===false)throw Error('MEDIA_ATTACHMENT_CAPTURE_ENDED: Đã dừng lượt tải trước khi bấm liên kết.');await link.click({timeout:5000,noWaitAfter:true})}finally{await link.evaluate((node,{type,temporaryDownload})=>{if(node.tagName==='BUTTON'){if(type===null)node.removeAttribute('type');else node.setAttribute('type',type)}if(temporaryDownload&&node.getAttribute('download')==='')node.removeAttribute('download')},{type:previousType,temporaryDownload}).catch(()=>{})}

}
export async function readPageAttachment(frame,media,signal,{timeoutMs=15000}={}){
  const page=frame.page?frame.page():frame,guard=await captureGuard(page,media.kind==='image'),epoch=guard?.epoch;let captured,success=false,triggered=false;
  try{return await new Promise((resolve,reject)=>{
    let settled=false;let timer=setTimeout(()=>finish(Error('MEDIA_ATTACHMENT_NOT_DELIVERED: Muse chưa trả tệp sau khi bấm liên kết tải.')),timeoutMs);
    const abort=()=>finish(signal.reason||Error('ABORTED'));
    const changed=()=>{if(!captured)finish(Error('MEDIA_ATTACHMENT_DOCUMENT_CHANGED: Trang Muse đã tải lại trong lúc nhận tệp; dùng Nhận lại từ Muse để lấy đúng kết quả.'))};
    const downloaded=async item=>{
      if(captured||settled)return;
      if(guard){try{await guard.refresh()}catch{finish(Error('MEDIA_ATTACHMENT_DOCUMENT_CHANGED'));return}if(settled||guard.epoch!==epoch){if(guard.blocked)await discardDownload(item);return}}
      if(captured||settled)return;captured=item;clearTimeout(timer);timer=setTimeout(()=>finish(Error('MEDIA_ATTACHMENT_DOWNLOAD_TIMEOUT')),120000);
      try{const stream=await item.createReadStream();if(!stream)throw Error('MEDIA_ATTACHMENT_READ_FAILED');let size=0;const chunks=[];for await(const chunk of stream){signal.throwIfAborted();if(settled)return;size+=chunk.length;if(size>100*1024*1024)throw Error('MEDIA_TOO_LARGE');chunks.push(Buffer.from(chunk));}if(!size)throw Error('MEDIA_EMPTY');finish(null,{base64:Buffer.concat(chunks).toString('base64'),mimeType:'application/octet-stream'});}catch(error){finish(error)}
    };
    function finish(error,value){if(settled)return;settled=true;success=!error;if(error&&media.kind==='image'&&triggered&&!captured&&guard?.epoch===epoch){guard.blocked=true;if(!signal.aborted)error=Error(error.message+'\n'+uncertainImageCapture().message,{cause:error})}clearTimeout(timer);signal.removeEventListener('abort',abort);page.off('download',downloaded);guard?.changed.delete(changed);error?reject(error):resolve(value)}
    signal.addEventListener('abort',abort,{once:true});page.on('download',downloaded);
    guard?.changed.add(changed);
    if(signal.aborted){abort();return}void clickNativeAttachment(frame,media,signal,{onTrigger:()=>{if(settled||(guard&&guard.epoch!==epoch))return false;triggered=true;return true}}).catch(error=>finish(error));
  })}finally{if(!success&&captured)await captured.cancel().catch(()=>{})}
}
