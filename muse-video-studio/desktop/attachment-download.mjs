import{mkdtemp,readFile,rm}from'node:fs/promises';import os from'node:os';import path from'node:path';
const imageCaptureGuards=new WeakMap();
const uncertainImageCapture=()=>Error('MEDIA_ATTACHMENT_UNCERTAIN: Lượt tải ảnh trước chưa xác nhận xong; chưa bấm tải tệp tiếp để tránh ghép nhầm cảnh. Bấm Tải lại Muse, rồi Nhận lại từ Muse; không cần tạo lại ảnh.');
function captureGuard(contents,create){
  let guard=imageCaptureGuards.get(contents);if(!guard&&!create)return null;
  if(!guard){
    const session=contents.session;guard={epoch:0,blocked:false,owners:new Set([contents]),changed:new Set()};imageCaptureGuards.set(contents,guard);
    const popup=child=>{guard.owners.add(child.webContents);child.webContents.once('destroyed',()=>guard.owners.delete(child.webContents))};
    const download=(event,item,sender)=>{if(guard.blocked&&guard.owners.has(sender)){event.preventDefault();try{item.cancel()}catch{}}};
    // Only a committed document navigation clears uncertainty. Hash/history
    // changes use did-navigate-in-page and leave this guard in place.
    const navigated=()=>{guard.epoch++;guard.blocked=false;for(const changed of [...guard.changed])changed()};
    contents.on('did-create-window',popup);contents.on('did-navigate',navigated);session.on('will-download',download);
    contents.once('destroyed',()=>{session.off('will-download',download);contents.off('did-create-window',popup);contents.off('did-navigate',navigated);imageCaptureGuards.delete(contents)});
  }
  if(guard.blocked)throw uncertainImageCapture();return guard;
}
// This stays in the main process and is not exposed as a remote-page bridge.
// The service's existing click handler supplies the bytes via an actual download.
export async function captureSessionAttachment(contents,trigger,signal,{timeoutMs=15000,kind}={}){
  const guard=captureGuard(contents,kind==='image'),epoch=guard?.epoch;let triggered=false;
  const directory=await mkdtemp(path.join(os.tmpdir(),'muse-native-file-'));const destination=path.join(directory,'attachment.bin'),session=contents.session,owners=new Set([contents]);let item;
  try{return await new Promise((resolve,reject)=>{
    let settled=false;let timer=setTimeout(()=>finish(Error('MEDIA_ATTACHMENT_NOT_DELIVERED: Muse chưa trả tệp sau khi bấm liên kết tải.')),timeoutMs);
    const abort=()=>{item?.cancel();finish(signal.reason||Error('ABORTED'))};
    const changed=()=>{if(!item)finish(Error('MEDIA_ATTACHMENT_DOCUMENT_CHANGED: Trang Muse đã tải lại trong lúc nhận tệp; dùng Nhận lại từ Muse để lấy đúng kết quả.'))};
    const popup=child=>owners.add(child.webContents);
    const download=(_event,value,sender)=>{
      if(item||settled||!owners.has(sender))return;item=value;clearTimeout(timer);timer=setTimeout(()=>finish(Error('MEDIA_ATTACHMENT_DOWNLOAD_TIMEOUT')),120000);
      if(value.getTotalBytes()>100*1024*1024){value.cancel();finish(Error('MEDIA_TOO_LARGE'));return;}
      value.setSavePath(destination);
      value.on('updated',()=>{if(value.getReceivedBytes()>100*1024*1024){value.cancel();finish(Error('MEDIA_TOO_LARGE'))}});
      value.once('done',async(_event,state)=>{
        if(settled)return;
        try{if(state!=='completed')throw Error('MEDIA_ATTACHMENT_DOWNLOAD_'+state.toUpperCase());const bytes=await readFile(destination);signal.throwIfAborted();if(!bytes.length)throw Error('MEDIA_EMPTY');if(bytes.length>100*1024*1024)throw Error('MEDIA_TOO_LARGE');finish(null,{base64:bytes.toString('base64'),mimeType:value.getMimeType()||'application/octet-stream'});}catch(error){finish(error)}
      });
    };
    function finish(error,value){if(settled)return;settled=true;if(error&&kind==='image'&&triggered&&!item&&guard?.epoch===epoch){guard.blocked=true;if(!signal.aborted)error=Error(error.message+'\n'+uncertainImageCapture().message,{cause:error})}clearTimeout(timer);session.off('will-download',download);contents.off('did-create-window',popup);signal.removeEventListener('abort',abort);guard?.changed.delete(changed);error?reject(error):resolve(value)}
    signal.addEventListener('abort',abort,{once:true});contents.on('did-create-window',popup);session.on('will-download',download);
    guard?.changed.add(changed);
    if(signal.aborted){abort();return;}
    void trigger(()=>{if(settled||(guard&&guard.epoch!==epoch))return false;triggered=true;return true}).catch(error=>finish(error));
  })}finally{if(item?.getState()==='progressing')item.cancel();await rm(directory,{recursive:true,force:true,maxRetries:3,retryDelay:100})}
}
