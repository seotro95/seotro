import{mkdtemp,readFile,rm}from'node:fs/promises';import os from'node:os';import path from'node:path';
// This stays in the main process and is not exposed as a remote-page bridge.
// The service's existing click handler supplies the bytes via an actual download.
export async function captureSessionAttachment(contents,trigger,signal,{timeoutMs=15000}={}){
  const directory=await mkdtemp(path.join(os.tmpdir(),'muse-native-file-'));const destination=path.join(directory,'attachment.bin'),session=contents.session,owners=new Set([contents]);let item;
  try{return await new Promise((resolve,reject)=>{
    let settled=false;let timer=setTimeout(()=>finish(Error('MEDIA_ATTACHMENT_NOT_DELIVERED: Muse chưa trả tệp sau khi bấm liên kết tải.')),timeoutMs);
    const abort=()=>{item?.cancel();finish(signal.reason||Error('ABORTED'))};
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
    function finish(error,value){if(settled)return;settled=true;clearTimeout(timer);session.off('will-download',download);contents.off('did-create-window',popup);signal.removeEventListener('abort',abort);error?reject(error):resolve(value)}
    signal.addEventListener('abort',abort,{once:true});contents.on('did-create-window',popup);session.on('will-download',download);
    if(signal.aborted){abort();return;}
    void trigger().catch(error=>finish(error));
  })}finally{if(item?.getState()==='progressing')item.cancel();await rm(directory,{recursive:true,force:true,maxRetries:3,retryDelay:100})}
}
