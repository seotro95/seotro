import http from 'node:http';
import { randomUUID } from 'node:crypto';
const escapeHTML = text => text.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');

export function createMuseFixture({ image, clip }) {
const state = { behavior: 'video', submitted: [], stops: 0, hold: false, peak: 0, pending: new Map(), released: new Set(), outputs: new Map(), uniqueImages: false, oldConversation: false, newChat: true, prehydrationInput: false, richComposer: false, hydrationDelayMs: 0, hydrateOnFocus: false, initialMode: 'none', authStatus: 200, loginInPopup: false, composerLayout: 'hatch', landingOnly: false, editorLabel: 'Message', chatPath: '', frameComposer: false };
const fixture = http.createServer(async (req, res) => {
  if (req.url === '/fixture-otp/request') {
    state.otpRequests = (state.otpRequests || 0) + 1;
    state.otpChallenge = randomUUID();
    state.otpCode = state.otpRequests === 1 ? '246810' : '135791';
    state.otpUsed = false;
    res.writeHead(200, { 'Content-Type': 'application/json', 'Set-Cookie': `fixture_pending=${state.otpChallenge}; HttpOnly; SameSite=Strict; Path=/` });
    return res.end(JSON.stringify({ sent: true }));
  }
  if (req.url === '/fixture-otp/verify') {
    let text = ''; for await (const chunk of req) text += chunk;
    const { code } = JSON.parse(text);
    const pending = req.headers.cookie?.split('; ').find(cookie => cookie.startsWith('fixture_pending='))?.split('=')[1];
    if (pending !== state.otpChallenge || state.otpUsed || code !== state.otpCode) {
      res.writeHead(400, { 'Content-Type': 'application/json' }); return res.end(JSON.stringify({ error: 'Mã không đúng hoặc đã hết hạn' }));
    }
    state.otpUsed = true;
    res.writeHead(200, { 'Content-Type': 'application/json', 'Set-Cookie': 'fixture_session=connected; HttpOnly; SameSite=Strict; Path=/' });
    return res.end(JSON.stringify({ verified: true }));
  }
  if (req.url?.startsWith('/fixture-email-verify?')) {
    const target = new URL(req.url, 'http://127.0.0.1');
    if (target.searchParams.get('ticket') !== 'fixture-email-ticket' || !/fixture_pending=sent/.test(req.headers.cookie || '') || state.emailUsed) { res.writeHead(400); return res.end('Email link is invalid or used'); }
    state.emailUsed = true;
    res.writeHead(302, { 'Set-Cookie': 'fixture_session=connected; Max-Age=3600; SameSite=Strict', Location: '/' }); return res.end();
  }
  if (req.url === '/initial-enter') { state.initialEnterEvents = (state.initialEnterEvents || 0) + 1; return res.end('ok'); }
  if (req.url === '/api/auth/check') {
    state.authChecks = (state.authChecks || 0) + 1;
    const signedIn = /fixture_session=connected/.test(req.headers.cookie || '');
    if (!signedIn && /fixture_pending=/.test(req.headers.cookie || '') && !state.otpUsed) {
      state.otpChecksDuringPending = (state.otpChecksDuringPending || 0) + 1;
      if (state.rejectAuthChecksDuringOtp) res.setHeader('Set-Cookie','fixture_pending=; Max-Age=0; HttpOnly; SameSite=Strict; Path=/');
    }
    res.statusCode = state.authStatus; res.setHeader('Content-Type', 'application/json'); return res.end(JSON.stringify({ ok: signedIn }));
  }
  if (req.url === '/fixture-auth-popup') { res.setHeader('Content-Type', 'text/html; charset=utf-8'); return res.end(`<html><button id="finish">Finish fixture login</button><script>document.querySelector('#finish').onclick=()=>{document.cookie='fixture_session=connected; Max-Age=3600; SameSite=Strict';setTimeout(()=>window.close(),50)}</script></html>`); }
  if (req.url === '/turn') {
    let text = ''; for await (const chunk of req) text += chunk;
    const incoming={...JSON.parse(text),authenticated:/fixture_session=connected/.test(req.headers.cookie||'')};
    (state.chatMessages||=[]).push(incoming);
    const parts=[...incoming.prompt.matchAll(/\[BEGIN_CLIP (CLIP_[a-z0-9_]+) (MUSE_[a-f0-9]{32})\]\n([\s\S]*?)\n\[END_CLIP \2\]/gi)];
    const tasks=parts.length?parts.map(part=>({...incoming,prompt:part[3],label:part[1],fileToken:part[2]})):[incoming];
    const modes=[];
    for(const task of tasks){
      const request={receivedAt:Date.now(),...task,id:state.submitted.length+1};
      request.fileToken||=request.prompt.match(/\bMUSE_[a-f0-9]{32}\b/)?.[0]||'';
      request.identity=req.headers.cookie?.split('; ').find(cookie=>cookie.startsWith('fixture_identity='))?.split('=')[1]||'';
      state.submitted.push(request);if(state.rejectConcurrency>0){request.rejectedForConcurrency=true;state.rejectConcurrency--;}
      const release=()=>{state.pending.delete(request.id);state.released.add(request.id)};state.pending.set(request.id,release);state.peak=Math.max(state.peak,state.pending.size);if(!state.hold)release();
      modes.push({behavior:state.refuseSceneIds?.includes(Number(request.label?.match(/CLIP_(\d+)/)?.[1]))?'reply':request.rejectedForConcurrency?'capacity':state.behavior,uniqueImages:state.uniqueImages,id:request.id,held:state.hold,conversationId:request.draftId||'',fileToken:state.omitAttribution?'':request.fileToken,label:state.labelReplies?(state.sourceClipLabels?'CLIP '+String(Number(request.prompt.trim().match(/^CLIP[ _-]*(\d+)/i)?.[1])||Number(request.label?.match(/CLIP_(\d+)/)?.[1])||1).padStart(3,'0'):request.label||''):'',blockedDownload:Boolean(state.blockedDownloadScenes?.includes(Number(request.label?.match(/CLIP_(\d+)/)?.[1]))),replyText:state.refuseSceneIds?.includes(Number(request.label?.match(/CLIP_(\d+)/)?.[1]))?request.label+': [mã cảnh] — the image could not be generated, and no file was created for this clip.\n\nWould you like a different adult character instead?\n\nThe other 4 portraits in this batch are done.':state.replyText||''});
    }
    res.setHeader('Content-Type','application/json');return res.end(JSON.stringify(parts.length?{jobs:modes}:modes[0]));
  }
  if (req.url?.startsWith('/ready?')) { res.setHeader('Content-Type', 'application/json'); return res.end(JSON.stringify({ ready: state.released.has(Number(new URL(req.url, 'http://127.0.0.1').searchParams.get('id'))) })); }
  if (req.url === '/capture') { let text = ''; for await (const chunk of req) text += chunk; const result = JSON.parse(text); state.outputs.set(result.id, result.base64); return res.end('ok'); }
  if (req.url === '/stop') { state.stops++; return res.end('ok'); }
  if(req.url?.startsWith('/native-file?')){if(!/fixture_session=connected/.test(req.headers.cookie||'')){res.writeHead(401);return res.end()}const id=Number(new URL(req.url,'http://127.0.0.1').searchParams.get('id'));(state.nativeDownloads||=[]).push(id);res.setHeader('Content-Type','image/png');res.setHeader('Content-Disposition','attachment; filename=provider-image.png');return res.end(state.outputs.has(id)?Buffer.from(state.outputs.get(id),'base64'):image);}
  if(req.url?.startsWith('/missing-view/')){(state.missingReads||=[]).push(req.url);res.writeHead(404,{'Content-Type':'text/plain'});return res.end('Use the site download action')}
  if(req.url?.startsWith('/file-view/')){res.setHeader('Content-Type','text/html');return res.end('<html>File viewer, not image bytes</html>')}
  if (req.url?.startsWith('/asset-file?')) { res.setHeader('Content-Type','image/png'); return res.end(image); }
  if (req.url?.endsWith('.png')) { (state.assetCookies||=[]).push(req.headers.cookie||''); res.setHeader('Content-Type', state.assetImageMime || 'image/png'); return res.end(state.assetImageBytes || image); }
  if (req.url?.endsWith('.mp4')) { if(state.videoNotReadyReads>0&&!req.url.startsWith('/old.')){state.videoNotReadyReads--;state.notReadyReads=(state.notReadyReads||0)+1;res.writeHead(404,{'Content-Type':'text/plain'});return res.end('File is still being prepared');}res.setHeader('Content-Type', 'video/mp4'); if(state.uniqueVideos){const request=state.submitted.find(row=>row.fileToken&&req.url.includes(row.fileToken))||state.submitted.find(row=>req.url==='/generated-'+row.id+'.mp4');const box=Buffer.alloc(12);box.writeUInt32BE(12,0);box.write('free',4);box.writeUInt32BE(request?.id||0,8);return res.end(Buffer.concat([clip,box]));}return res.end(state.assetVideoBytes||clip); }
  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  const requestPath = new URL(req.url, 'http://127.0.0.1').pathname;
  if(req.headers['sec-fetch-dest']==='document')state.pageLoads=(state.pageLoads||0)+1;
  if(state.draftRoutes&&requestPath.startsWith('/chat/')&&!state.submitted.some(row=>'/chat/'+row.draftId===requestPath)){res.writeHead(302,{Location:'/'});return res.end()}
  if (state.redirectChats && requestPath.startsWith('/chat/')) { res.writeHead(302, { Location: '/' }); return res.end(); }
  if (state.chatPath && requestPath === '/') return res.end('<!doctype html><html><body><h1>Fixture dashboard without chat</h1></body></html>');
  if (state.frameComposer && requestPath !== '/composer-frame') return res.end('<!doctype html><html><body><iframe title="Muse chat" src="/composer-frame" style="width:100%;height:900px;border:0"></iframe></body></html>');
  const rootTag = state.composerLayout === 'hatch' ? 'div' : 'form';
  const fixtureIdentity=req.headers.cookie?.split('; ').find(cookie=>cookie.startsWith('fixture_identity='))?.split('=')[1]||'';
  const sharedHistory = state.sharedHistory ? state.submitted.filter(request => (!state.isolateAccounts||request.identity===fixtureIdentity)&& (!state.chatRoutes || request.path === requestPath)).map(request => `<div data-message-item data-message-role="user">${escapeHTML(request.prompt)}</div>${state.outputs.has(request.id) ? `<div data-message-item data-message-role="assistant"><img src="data:${state.imageEncoding || 'image/png'};base64,${state.outputs.get(request.id)}"></div>` : ''}`).join('') : '';
  res.end(`<!doctype html><html><body>
  <header><span data-testid="token-balance">Tokens remaining: 1,234</span></header><button id="login">Fixture login</button><p id="popup-feedback"></p>
  ${state.otpLogin ? `<section id="otp-panel"><form id="otp-request"><label>Email<input type="email" aria-label="Email đăng nhập" required></label><button>Gửi mã</button></form><form id="otp-verify" style="display:none"><label>Mã<input type="text" inputmode="numeric" autocomplete="one-time-code" maxlength="6" aria-label="Mã xác nhận" required></label><button>Xác nhận mã</button></form><p id="otp-feedback" role="status"></p></section>` : ''}
  ${state.newChat ? state.iconNewChat?'<button id="new-chat" data-testid="new-chat-button">+</button>':'<button id="new-chat">New chat</button>' : ''}<div id="history">${state.oldConversation ? '<div data-message-item data-message-role="user">Old thread</div>' : ''}<div data-message-item data-message-role="assistant">OLD RESPONSE Tokens remaining: 999999<img src="/old.png"><video src="/old.mp4" preload="metadata"></video></div>${sharedHistory}</div>
  <${rootTag} id="fixture-composer" ${state.composerLayout === 'hatch' ? 'data-hatch-composer-root' : ''} style="display:none">${state.prehydrationInput ? `<textarea rows="1" aria-label="Message" placeholder="Message" data-hatch-composer-prehydration-input="true" style="display:${state.hydrationDelayMs || state.hydrateOnFocus || state.initialMode !== 'none' ? 'block' : 'none'}"></textarea>` : ''}${state.richComposer ? `<div id="fixture-editor" contenteditable="true" data-lexical-editor="true" role="textbox" aria-label="${state.editorLabel}" style="display:${state.hydrationDelayMs || state.hydrateOnFocus || state.initialMode !== 'none' ? 'none' : 'block'}"></div>` : `<textarea id="fixture-editor" aria-label="${state.editorLabel}"></textarea>`}${state.composerLayout === 'ambiguous' ? '<textarea aria-label="Message" id="other-editor"></textarea>' : ''}<input type="file" accept="image/*"><span id="attachments"></span></${rootTag}>
  <button data-testid="hatch-composer-stop-button" style="display:none">Stop</button>
  <script>
  if(${Boolean(state.poisonBlobFetch)}){const original=window.fetch;window.fetch=(input,...args)=>{if(/^blob:/i.test(typeof input==='string'?input:input?.url||''))return Promise.reject(new TypeError('Failed to fetch'));return original(input,...args)}}
  if(${Boolean(state.poisonMediaFetch)}){const nativeFetch=window.fetch;window.fetch=(input,...args)=>{const url=typeof input==='string'?input:input?.url;if(/\\.(png|mp4)(?:$|[?#])/i.test(url||''))return Promise.reject(new TypeError('Failed to fetch'));return nativeFetch(input,...args)}}
  let draftId='';const root=document.querySelector('#fixture-composer');let editor=root.querySelector('#fixture-editor');const history=document.querySelector('#history');const stop=document.querySelector('[data-testid="hatch-composer-stop-button"]');
  const sharedChannel=${Boolean(state.sharedLiveHistory)}?new BroadcastChannel('fixture-shared-history'):null;
  if(sharedChannel)sharedChannel.onmessage=event=>{const user=document.createElement('div');user.setAttribute('data-message-item','');user.setAttribute('data-message-role','user');user.textContent=event.data;history.appendChild(user)};
  const prehydration=root.querySelector('[data-hatch-composer-prehydration-input]');let prehydrationFocus=0;let prehydrationInputEvents=0;
  const hydrate=()=>{if(${state.initialMode === 'input'})editor.textContent=prehydration.value;prehydration?.style.setProperty('display','none');editor.style.display='block'};if(${state.initialMode === 'functional' || state.initialMode === 'inert'})editor=prehydration;
  if(prehydration){prehydration.addEventListener('input',()=>{prehydrationInputEvents++;if(${state.initialMode === 'input'})hydrate()});prehydration.addEventListener('focus',()=>{prehydrationFocus++;if(${state.hydrateOnFocus})setTimeout(hydrate,${state.hydrationDelayMs})})}
  if(${state.initialMode === 'inert'})prehydration.addEventListener('keydown',event=>{if(event.key==='Enter')fetch('/initial-enter')});
  if(${!state.hydrateOnFocus && state.hydrationDelayMs > 0})setTimeout(hydrate,${state.hydrationDelayMs});
  let conversationOpen=${!state.landingOnly};
  const signedInFromServer=${/fixture_session=connected/.test(req.headers.cookie || '')};
  function ready(){const signedIn=document.cookie.includes('fixture_session=connected')||signedInFromServer;root.style.display=signedIn&&conversationOpen&&(!${Boolean(state.requireSessionStorage)}||sessionStorage.getItem('fixture_scope')==='fixture-session-owned')?'block':'none';if(document.querySelector('#otp-panel'))document.querySelector('#otp-panel').style.display=signedIn?'none':'block'};ready();
  if(document.querySelector('#otp-request')){
    document.querySelector('#otp-request').onsubmit=async event=>{event.preventDefault();await fetch('/fixture-otp/request',{method:'POST'});document.querySelector('#otp-verify').style.display='block';document.querySelector('#otp-feedback').textContent='Đã gửi mã mới'};
    document.querySelector('#otp-verify').onsubmit=async event=>{event.preventDefault();const response=await fetch('/fixture-otp/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:document.querySelector('#otp-verify input').value})});const result=await response.json();if(response.ok){location.href='/';return}document.querySelector('#otp-feedback').textContent=result.error};
  }
  document.querySelector('#new-chat')?.addEventListener('click',()=>{if(${Boolean(state.hashRoutes)}){history.replaceChildren();draftId=crypto.randomUUID();location.hash='/chat/'+draftId;conversationOpen=true;ready();return}if(${Boolean(state.chatRoutes)}){location.href='/chat/'+crypto.randomUUID();return}history.replaceChildren();draftId=crypto.randomUUID();conversationOpen=true;ready()});
  document.querySelector('#login').onclick=()=>{if(${Boolean(state.emailLogin)}){document.cookie='fixture_pending=sent; Max-Age=3600; SameSite=Strict';document.querySelector('#popup-feedback').textContent='Email sent';return}if(${state.loginInPopup === 'blank'}){const popup=window.open('about:blank');if(!popup){document.querySelector('#popup-feedback').textContent='Popup blocked';return}setTimeout(()=>{popup.location.href='/fixture-auth-popup'},50);return}if(${Boolean(state.loginInPopup)}){window.open('/fixture-auth-popup');return}document.cookie='fixture_session=connected; Max-Age=3600; SameSite=Strict';if(${Boolean(state.requireSessionStorage)})sessionStorage.setItem('fixture_scope','fixture-session-owned');ready()};
  root.querySelector('input').onchange=e=>{const img=new Image();img.src=URL.createObjectURL(e.target.files[0]);document.querySelector('#attachments').appendChild(img)};
  stop.onclick=()=>{stop.style.display=${JSON.stringify(state.keepStreamingAfterMedia?'block':'none')};fetch('/stop')};
  if(${state.initialMode !== 'inert'})editor.onkeydown=async e=>{if(e.key!=='Enter')return;e.preventDefault();const prompt=editor.tagName==='TEXTAREA'?editor.value:editor.innerText;const user=document.createElement('div');user.setAttribute('data-message-item','');user.setAttribute('data-message-role','user');user.textContent=${Boolean(state.collapsedUserMessages)}?prompt.slice(0,180):prompt;history.appendChild(user);sharedChannel?.postMessage(prompt);if(editor.tagName==='TEXTAREA')editor.value='';else editor.replaceChildren();const attached=root.querySelectorAll('img').length;document.querySelector('#attachments').replaceChildren();root.querySelector('input').value='';stop.style.display='block';
    const envelope=await(await fetch('/turn',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt,attached,draftId,visibility:document.visibilityState,href:location.href,path:location.pathname,viewport:{width:innerWidth,height:innerHeight},prehydrationValue:prehydration?.value||'',prehydrationFocus,prehydrationInputEvents,initialMode:${JSON.stringify(state.initialMode)}})})).json();
    const combinedReply=${Boolean(state.combineReplies)}?document.createElement('div'):null;if(combinedReply){combinedReply.setAttribute('data-message-item','');combinedReply.setAttribute('data-message-role','assistant');}
    if(${Boolean(state.progressCaptions)}){const ack=document.createElement('div');ack.setAttribute('data-message-item','');ack.setAttribute('data-message-role','assistant');ack.textContent='I’ll send each one as it finishes.';history.appendChild(ack);}
    for(const mode of envelope.jobs||[envelope]){(async()=>{
    if(${Boolean(state.draftRoutes)}&&mode.conversationId)window.history.replaceState(null,'','/chat/'+mode.conversationId);
    if(${Boolean(state.backgroundGeneration)}){const ack=document.createElement('div');ack.setAttribute('data-message-item','');ack.setAttribute('data-message-role','assistant');ack.textContent='Started generation '+(mode.fileToken||'');history.appendChild(ack);stop.style.display='none';}
    if(mode.held) while(!(await(await fetch('/ready?id='+mode.id)).json()).ready) await new Promise(resolve=>setTimeout(resolve,80));
    if(mode.behavior==='slow')return;
    setTimeout(()=>{if(${Boolean(state.foreignTurn)}){const foreign=document.createElement('div');foreign.setAttribute('data-message-item','');foreign.setAttribute('data-message-role','user');foreign.textContent='A different user request after the current prompt';history.appendChild(foreign)}const reply=document.createElement('div');reply.setAttribute('data-message-item','');reply.setAttribute('data-message-role','assistant');if(mode.label&&!${Boolean(state.separateCaptions)}){const heading=document.createElement('h3');heading.textContent=mode.label;reply.appendChild(heading)}
      if(${Boolean(state.distractorLink)}&&mode.fileToken){const link=document.createElement('a');link.href='sandbox:/mnt/data/'+mode.fileToken+'.'+(mode.behavior==='image'?'png':'mp4');link.textContent=mode.fileToken;reply.appendChild(link)}
      if(mode.behavior==='video'){if(mode.fileToken&&!${Boolean(state.videoSourceToken)}){const link=document.createElement('a');link.href='/'+mode.fileToken+'.mp4';link.download=mode.fileToken+'.mp4';link.textContent=mode.fileToken;reply.appendChild(link)}else if(${Boolean(state.videoDownloadLink)}){const link=document.createElement('a');link.href='/new.mp4';link.download='generated.mp4';link.textContent='Download video';reply.appendChild(link)}else{const video=document.createElement('video');if(mode.fileToken)video.setAttribute('aria-label',mode.fileToken);video.preload=${JSON.stringify(state.lazyVideo?'none':'metadata')};if(${Boolean(state.videoSourceTag)}){const source=document.createElement('source');source.src='/new.mp4';source.type='video/mp4';video.appendChild(source)}else video.src=${Boolean(state.uniqueVideos)}?'/generated-'+mode.id+'.mp4':'/new.mp4';reply.appendChild(video)}}
      else if(mode.behavior==='image'){if(${Boolean(state.nativeImageDownload)}){const canvas=document.createElement('canvas');canvas.width=360;canvas.height=640;const ctx=canvas.getContext('2d');ctx.fillStyle='hsl('+mode.id*39+' 65% 35%)';ctx.fillRect(0,0,360,640);ctx.fillStyle='white';ctx.fillText('Native image '+mode.id,20,80);const bytes=canvas.toDataURL();const stored=fetch('/capture',{method:'POST',body:JSON.stringify({id:mode.id,base64:bytes.split(',')[1]})});const link=document.createElement(${JSON.stringify(state.nativeDownloadButton?'button':'a')});if(link.tagName==='A')link.href=mode.blockedDownload?'javascript:window.unexpectedMediaAction=true':${JSON.stringify(state.nativeHrefBase||'sandbox:/mnt/data/')}+mode.fileToken+'.png';if(mode.blockedDownload)link.download=mode.fileToken+'.png';link.textContent=${Boolean(state.nativeDownloadButton)}?'Download image':mode.fileToken||'Download image';if(${Boolean(state.nativeBlobDownload)}){const bin=Uint8Array.from(atob(bytes.split(',')[1]),ch=>ch.charCodeAt(0));link.href=URL.createObjectURL(new Blob([bin],{type:'image/png'}));link.download='generated.png';}else link.onclick=async event=>{event.preventDefault();if(mode.blockedDownload)return;if(${Boolean(state.requireTrustedDownload)}&&!event.isTrusted)return;await stored;const response=await fetch('/native-file?id='+mode.id);const blob=await response.blob();const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='native-image-'+mode.id+'.png';document.body.appendChild(a);a.click();a.remove();};reply.appendChild(link)}else if(${Boolean(state.onlySandboxImage)}){}else if(${Boolean(state.extensionlessImage)}){const link=document.createElement('a');link.href='/asset-file?id='+mode.id;link.textContent=mode.fileToken;reply.appendChild(link)}else{const img=document.createElement('img');if(mode.fileToken)img.alt=mode.fileToken;if(mode.uniqueImages){const canvas=document.createElement('canvas');canvas.width=640;canvas.height=360;const ctx=canvas.getContext('2d');ctx.fillStyle='#172340';ctx.fillRect(0,0,640,360);ctx.fillStyle='#ffffff';ctx.font='32px sans-serif';ctx.fillText('FIXTURE IMAGE '+mode.id,30,180);img.src=canvas.toDataURL(${JSON.stringify(state.imageEncoding || 'image/png')});fetch('/capture',{method:'POST',body:JSON.stringify({id:mode.id,base64:img.src.split(',')[1]})})}else img.src='/new.png';if(${Boolean(state.lazyImage)}){img.dataset.src=img.src;img.removeAttribute('src')}reply.appendChild(img)}}
      else if(mode.behavior==='capacity'){reply.textContent=mode.fileToken||'';reply.innerHTML+='<span data-testid="assistant-response-error-notice">Too many simultaneous generations. Only one generation at a time.</span>'}
      else if(mode.behavior==='reply'){reply.textContent=mode.replyText}
      else if(mode.behavior==='clarify'){reply.textContent=(mode.fileToken||'')+' Please clarify the image you want; provide a specific scene description.'}
      else if(mode.behavior==='error'){reply.innerHTML='<span data-testid="assistant-response-error-notice">429 quota exhausted</span>'}
      else reply.textContent='A new cinematic prompt, not old history.';
      if(combinedReply){reply.removeAttribute('data-message-item');reply.removeAttribute('data-message-role');combinedReply.appendChild(reply);if(!combinedReply.isConnected)history.appendChild(combinedReply)}else history.appendChild(reply);
      if(${Boolean(state.separateCaptions)}&&mode.label){const caption=document.createElement('div');caption.setAttribute('data-message-item','');caption.setAttribute('data-message-role','assistant');const heading=document.createElement('h3');heading.textContent=${Boolean(state.labelOnly)}?'- '+mode.label+':':mode.label;caption.appendChild(heading);const done=document.createElement('p');done.textContent='Done — independent landscape '+mode.id+'. 1280 × 720 (720p), 10 seconds, 16:9, 24 fps.';if(!${Boolean(state.labelOnly)})caption.appendChild(done);const finish=()=>{if(${Boolean(state.labelBeforeMedia)})reply.before(caption);else reply.after(caption);if(${Boolean(state.progressCaptions)}&&/CLIP_00[23]_/.test(mode.label)){const notice=document.createElement('div');notice.setAttribute('data-message-item','');notice.setAttribute('data-message-role','assistant');notice.textContent=/CLIP_002_/.test(mode.label)?'One still running — CLIP_002, the shallow depression — I’ll send it as soon as it finishes.':'Two still running — I’ll send each one as it finishes.';if(${Boolean(state.labelBeforeMedia)})reply.before(notice);else reply.after(notice)}};if(${Number(state.captionDelayMs)||0})setTimeout(finish,${Number(state.captionDelayMs)||0});else finish();}
      stop.style.display=${JSON.stringify(state.keepStreamingAfterMedia?'block':'none')};},100);
    })();}
  };
  if(${Boolean(state.missingComposer)})root.remove();
  </script></body></html>`);
});

return { server: fixture, state, releaseAll() { for (const release of [...state.pending.values()]) release(); } };
}
