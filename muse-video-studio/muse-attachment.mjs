// Activate only an existing media download control in the owned Muse frame. This does
// not turn sandbox paths into local paths, guess an API, or ask for generation.
export function nativeAttachmentURL(value){
  try{const url=new URL(value);return !url.username&&!url.password&&(['attachment:','artifact:'].includes(url.protocol)||(url.protocol==='sandbox:'&&Boolean(url.pathname||url.hostname)))}catch{return false}
}
export async function clickNativeAttachment(frame,media,signal){
  signal.throwIfAborted();if(!media.nativeControl&&!nativeAttachmentURL(media.src))throw Error('MEDIA_URL_UNSUPPORTED');
  const id=await frame.evaluate(({src,nativeId,nativeButton,nativeControl})=>{
    const matches=[...document.querySelectorAll(nativeButton?'button,[role="button"]':'a[href]')].filter(node=>nativeButton?node.dataset.museStudioFileId===nativeId:(()=>{try{return new URL(node.getAttribute('href'),location.href).href===src}catch{return false}})());
    const node=matches.find(item=>nativeId&&item.dataset.museStudioFileId===nativeId)||(matches.length===1?matches[0]:null);
    if(!node)return null;
    if(!nativeButton){const url=new URL(node.getAttribute('href'),location.href);if(url.username||url.password||/^(?:javascript|vbscript|mailto|tel|sms|intent|shell|ms-[a-z-]+):$/i.test(url.protocol))return null;}
    else{const name=[node.getAttribute('aria-label'),node.getAttribute('title'),node.innerText].join(' ');if(!/\bdownload\b|\bsave (?:image|video|file)\b|tải (?:xuống|về|ảnh|video|tệp|file)/i.test(name)||/\b(?:all|zip|generate|create)\b|tất cả|tạo (?:ảnh|video)/i.test(name))return null;}
    node.dataset.museStudioFileId||=crypto.randomUUID();
    // Run the site's existing download handler, then suppress only the default
    // link navigation. Virtual/file URIs are never fetched or read on the host.
    const browserDownload=!nativeButton&&node.hasAttribute('download')&&/^(?:https?:|blob:|filesystem:|data:(?:image|video)\/)/i.test(node.href||node.getAttribute('href')||'');
    const protect=event=>{if(event.target===node||node.contains(event.target)){if(!browserDownload)event.preventDefault();cleanup()}};
    const cleanup=()=>{clearTimeout(timer);window.removeEventListener('click',protect)};
    const timer=setTimeout(cleanup,6000);window.addEventListener('click',protect);
    return node.dataset.museStudioFileId;
  },{src:media.src,nativeId:media.nativeId,nativeButton:Boolean(media.nativeButton),nativeControl:Boolean(media.nativeControl)});
  if(!id)throw Error('MEDIA_ATTACHMENT_LINK_CHANGED: Chưa xác định được đúng liên kết tệp Muse.');
  const link=frame.locator(`[data-muse-studio-file-id="${id}"]`);
  // A trusted browser click preserves the user gesture required by some
  // service download handlers. It still targets only the matched control.
  const previousType=await link.evaluate(node=>{const type=node.getAttribute('type');if(node.tagName==='BUTTON')node.setAttribute('type','button');return type});
  try{await link.click({timeout:5000,noWaitAfter:true})}finally{await link.evaluate((node,type)=>{if(node.tagName==='BUTTON'){if(type===null)node.removeAttribute('type');else node.setAttribute('type',type)}},previousType).catch(()=>{})}

}
export async function readPageAttachment(frame,media,signal,{timeoutMs=15000}={}){
  const page=frame.page?frame.page():frame;let captured,success=false;
  try{return await new Promise((resolve,reject)=>{
    let settled=false;let timer=setTimeout(()=>finish(Error('MEDIA_ATTACHMENT_NOT_DELIVERED: Muse chưa trả tệp sau khi bấm liên kết tải.')),timeoutMs);
    const abort=()=>finish(signal.reason||Error('ABORTED'));
    const downloaded=async item=>{
      if(captured||settled)return;captured=item;clearTimeout(timer);timer=setTimeout(()=>finish(Error('MEDIA_ATTACHMENT_DOWNLOAD_TIMEOUT')),120000);
      try{const stream=await item.createReadStream();if(!stream)throw Error('MEDIA_ATTACHMENT_READ_FAILED');let size=0;const chunks=[];for await(const chunk of stream){signal.throwIfAborted();if(settled)return;size+=chunk.length;if(size>100*1024*1024)throw Error('MEDIA_TOO_LARGE');chunks.push(Buffer.from(chunk));}if(!size)throw Error('MEDIA_EMPTY');finish(null,{base64:Buffer.concat(chunks).toString('base64'),mimeType:'application/octet-stream'});}catch(error){finish(error)}
    };
    function finish(error,value){if(settled)return;settled=true;success=!error;clearTimeout(timer);signal.removeEventListener('abort',abort);page.off('download',downloaded);error?reject(error):resolve(value)}
    signal.addEventListener('abort',abort,{once:true});page.on('download',downloaded);
    if(signal.aborted){abort();return}void clickNativeAttachment(frame,media,signal).catch(error=>finish(error));
  })}finally{if(!success&&captured)await captured.cancel().catch(()=>{})}
}
