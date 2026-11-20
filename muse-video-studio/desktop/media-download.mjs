const maxBytes=100*1024*1024;
// Called by the trusted driver, never exposed as a bridge to the Muse page.
// session.fetch uses this account's Electron cookies and proxy, without page CORS.
export async function readSessionMedia(session,src,{signal,serviceURL}={}){
  const allowed=value=>{const url=new URL(value);if(url.username||url.password||!(url.protocol==='https:'||(url.protocol==='http:'&&url.hostname==='127.0.0.1'&&url.origin===new URL(serviceURL).origin)))throw Error('MEDIA_URL_UNSUPPORTED');return url.href};
  const control=new AbortController();const combined=signal?AbortSignal.any([signal,control.signal]):control.signal;
  const timer=setTimeout(()=>control.abort(Error('MEDIA_DOWNLOAD_TIMEOUT')),120000);timer.unref?.();
  try{
    let url=allowed(src),response;
    for(let redirects=0;redirects<=5;redirects++){
      combined.throwIfAborted();response=await session.fetch(url,{credentials:'include',redirect:'manual',signal:combined});
      if(![301,302,303,307,308].includes(response.status))break;
      const location=response.headers.get('location');await response.body?.cancel();if(!location||redirects===5)throw Error('MEDIA_REDIRECT_INVALID');url=allowed(new URL(location,url).href);
    }
    if(!response.ok)throw Error(`MEDIA_HTTP_${response.status}`);
    const mimeType=(response.headers.get('content-type')||'').split(';')[0].trim();
    if(/^(?:text\/html|application\/json)$/.test(mimeType)){await response.body?.cancel();throw Error('MEDIA_RESPONSE_NOT_MEDIA')}
    if(Number(response.headers.get('content-length'))>maxBytes){await response.body?.cancel();throw Error('MEDIA_TOO_LARGE')}
    const chunks=[];let bytes=0;
    if(!response.body)throw Error('MEDIA_EMPTY');
    const reader=response.body.getReader();try{for(;;){combined.throwIfAborted();const row=await reader.read();if(row.done)break;bytes+=row.value.byteLength;if(bytes>maxBytes){await reader.cancel();throw Error('MEDIA_TOO_LARGE')}chunks.push(Buffer.from(row.value))}}finally{reader.releaseLock()}
    if(!bytes)throw Error('MEDIA_EMPTY');return {base64:Buffer.concat(chunks).toString('base64'),mimeType};
  }finally{clearTimeout(timer)}
}
