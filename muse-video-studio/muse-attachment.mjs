// Activate only an existing media-file link in the owned Muse frame. This does
// not turn sandbox paths into local paths, guess an API, or ask for generation.
export function nativeAttachmentURL(value){
  try{const url=new URL(value);return !url.username&&!url.password&&(['attachment:','artifact:'].includes(url.protocol)||(url.protocol==='sandbox:'&&url.pathname.startsWith('/mnt/data/')))}catch{return false}
}
export async function clickNativeAttachment(frame,media,signal){
  signal.throwIfAborted();if(!nativeAttachmentURL(media.src))throw Error('MEDIA_URL_UNSUPPORTED');
  const id=await frame.evaluate(({src,nativeId})=>{
    const matches=[...document.querySelectorAll('a[href]')].filter(link=>{try{return new URL(link.getAttribute('href'),location.href).href===src}catch{return false}});
    const link=matches.find(node=>nativeId&&node.dataset.museStudioFileId===nativeId)||(matches.length===1?matches[0]:null);
    if(!link)return null;link.dataset.museStudioFileId||=crypto.randomUUID();
    // Let the site's React/download handlers run, but prevent a plain virtual
    // href from replacing the chat with a browser error page when no handler exists.
    const protect=event=>{if(event.target?.closest?.('a')===link){event.preventDefault();cleanup()}};
    const cleanup=()=>{clearTimeout(timer);window.removeEventListener('click',protect)};
    const timer=setTimeout(cleanup,6000);window.addEventListener('click',protect);
    return link.dataset.museStudioFileId;
  },{src:media.src,nativeId:media.nativeId});
  if(!id)throw Error('MEDIA_ATTACHMENT_LINK_CHANGED: Chưa xác định được đúng liên kết tệp Muse.');
  const link=frame.locator(`a[data-muse-studio-file-id="${id}"]`);
  await link.click({timeout:5000,noWaitAfter:true});
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
