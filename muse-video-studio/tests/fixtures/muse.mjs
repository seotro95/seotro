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
    const request = { ...JSON.parse(text), id: state.submitted.length + 1, authenticated: /fixture_session=connected/.test(req.headers.cookie || '') };
    request.identity=req.headers.cookie?.split('; ').find(cookie=>cookie.startsWith('fixture_identity='))?.split('=')[1]||'';
    state.submitted.push(request);
    const release = () => { state.pending.delete(request.id); state.released.add(request.id); };
    state.pending.set(request.id, release); state.peak = Math.max(state.peak, state.pending.size);
    if (!state.hold) release();
    res.setHeader('Content-Type', 'application/json');
    return res.end(JSON.stringify({ behavior: state.behavior, uniqueImages: state.uniqueImages, id: request.id, held: state.hold }));
  }
  if (req.url?.startsWith('/ready?')) { res.setHeader('Content-Type', 'application/json'); return res.end(JSON.stringify({ ready: state.released.has(Number(new URL(req.url, 'http://127.0.0.1').searchParams.get('id'))) })); }
  if (req.url === '/capture') { let text = ''; for await (const chunk of req) text += chunk; const result = JSON.parse(text); state.outputs.set(result.id, result.base64); return res.end('ok'); }
  if (req.url === '/stop') { state.stops++; return res.end('ok'); }
  if (req.url?.endsWith('.png')) { res.setHeader('Content-Type', state.assetImageMime || 'image/png'); return res.end(state.assetImageBytes || image); }
  if (req.url?.endsWith('.mp4')) { res.setHeader('Content-Type', 'video/mp4'); return res.end(clip); }
  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  const requestPath = new URL(req.url, 'http://127.0.0.1').pathname;
  if (state.redirectChats && requestPath.startsWith('/chat/')) { res.writeHead(302, { Location: '/' }); return res.end(); }
  if (state.chatPath && requestPath === '/') return res.end('<!doctype html><html><body><h1>Fixture dashboard without chat</h1></body></html>');
  if (state.frameComposer && requestPath !== '/composer-frame') return res.end('<!doctype html><html><body><iframe title="Muse chat" src="/composer-frame" style="width:100%;height:900px;border:0"></iframe></body></html>');
  const rootTag = state.composerLayout === 'hatch' ? 'div' : 'form';
  const fixtureIdentity=req.headers.cookie?.split('; ').find(cookie=>cookie.startsWith('fixture_identity='))?.split('=')[1]||'';
  const sharedHistory = state.sharedHistory ? state.submitted.filter(request => (!state.isolateAccounts||request.identity===fixtureIdentity)&& (!state.chatRoutes || request.path === requestPath)).map(request => `<div data-message-item data-message-role="user">${escapeHTML(request.prompt)}</div>${state.outputs.has(request.id) ? `<div data-message-item data-message-role="assistant"><img src="data:${state.imageEncoding || 'image/png'};base64,${state.outputs.get(request.id)}"></div>` : ''}`).join('') : '';
  res.end(`<!doctype html><html><body>
  <header><span data-testid="token-balance">Tokens remaining: 1,234</span></header><button id="login">Fixture login</button><p id="popup-feedback"></p>
  ${state.otpLogin ? `<section id="otp-panel"><form id="otp-request"><label>Email<input type="email" aria-label="Email đăng nhập" required></label><button>Gửi mã</button></form><form id="otp-verify" style="display:none"><label>Mã<input type="text" inputmode="numeric" autocomplete="one-time-code" maxlength="6" aria-label="Mã xác nhận" required></label><button>Xác nhận mã</button></form><p id="otp-feedback" role="status"></p></section>` : ''}
  ${state.newChat ? '<button id="new-chat">New chat</button>' : ''}<div id="history">${state.oldConversation ? '<div data-message-item data-message-role="user">Old thread</div>' : ''}<div data-message-item data-message-role="assistant">OLD RESPONSE Tokens remaining: 999999<img src="/old.png"><video src="/old.mp4" preload="metadata"></video></div>${sharedHistory}</div>
  <${rootTag} id="fixture-composer" ${state.composerLayout === 'hatch' ? 'data-hatch-composer-root' : ''} style="display:none">${state.prehydrationInput ? `<textarea rows="1" aria-label="Message" placeholder="Message" data-hatch-composer-prehydration-input="true" style="display:${state.hydrationDelayMs || state.hydrateOnFocus || state.initialMode !== 'none' ? 'block' : 'none'}"></textarea>` : ''}${state.richComposer ? `<div id="fixture-editor" contenteditable="true" data-lexical-editor="true" role="textbox" aria-label="${state.editorLabel}" style="display:${state.hydrationDelayMs || state.hydrateOnFocus || state.initialMode !== 'none' ? 'none' : 'block'}"></div>` : `<textarea id="fixture-editor" aria-label="${state.editorLabel}"></textarea>`}${state.composerLayout === 'ambiguous' ? '<textarea aria-label="Message" id="other-editor"></textarea>' : ''}<input type="file" accept="image/*"><span id="attachments"></span></${rootTag}>
  <button data-testid="hatch-composer-stop-button" style="display:none">Stop</button>
  <script>
  const root=document.querySelector('#fixture-composer');let editor=root.querySelector('#fixture-editor');const history=document.querySelector('#history');const stop=document.querySelector('[data-testid="hatch-composer-stop-button"]');
  const prehydration=root.querySelector('[data-hatch-composer-prehydration-input]');let prehydrationFocus=0;let prehydrationInputEvents=0;
  const hydrate=()=>{if(${state.initialMode === 'input'})editor.textContent=prehydration.value;prehydration?.style.setProperty('display','none');editor.style.display='block'};if(${state.initialMode === 'functional' || state.initialMode === 'inert'})editor=prehydration;
  if(prehydration){prehydration.addEventListener('input',()=>{prehydrationInputEvents++;if(${state.initialMode === 'input'})hydrate()});prehydration.addEventListener('focus',()=>{prehydrationFocus++;if(${state.hydrateOnFocus})setTimeout(hydrate,${state.hydrationDelayMs})})}
  if(${state.initialMode === 'inert'})prehydration.addEventListener('keydown',event=>{if(event.key==='Enter')fetch('/initial-enter')});
  if(${!state.hydrateOnFocus && state.hydrationDelayMs > 0})setTimeout(hydrate,${state.hydrationDelayMs});
  let conversationOpen=${!state.landingOnly};
  const signedInFromServer=${/fixture_session=connected/.test(req.headers.cookie || '')};
  function ready(){const signedIn=document.cookie.includes('fixture_session=connected')||signedInFromServer;root.style.display=signedIn&&conversationOpen?'block':'none';if(document.querySelector('#otp-panel'))document.querySelector('#otp-panel').style.display=signedIn?'none':'block'};ready();
  if(document.querySelector('#otp-request')){
    document.querySelector('#otp-request').onsubmit=async event=>{event.preventDefault();await fetch('/fixture-otp/request',{method:'POST'});document.querySelector('#otp-verify').style.display='block';document.querySelector('#otp-feedback').textContent='Đã gửi mã mới'};
    document.querySelector('#otp-verify').onsubmit=async event=>{event.preventDefault();const response=await fetch('/fixture-otp/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:document.querySelector('#otp-verify input').value})});const result=await response.json();if(response.ok){location.href='/';return}document.querySelector('#otp-feedback').textContent=result.error};
  }
  document.querySelector('#new-chat')?.addEventListener('click',()=>{if(${Boolean(state.chatRoutes)}){location.href='/chat/'+crypto.randomUUID();return}history.replaceChildren();conversationOpen=true;ready()});
  document.querySelector('#login').onclick=()=>{if(${Boolean(state.emailLogin)}){document.cookie='fixture_pending=sent; Max-Age=3600; SameSite=Strict';document.querySelector('#popup-feedback').textContent='Email sent';return}if(${state.loginInPopup === 'blank'}){const popup=window.open('about:blank');if(!popup){document.querySelector('#popup-feedback').textContent='Popup blocked';return}setTimeout(()=>{popup.location.href='/fixture-auth-popup'},50);return}if(${Boolean(state.loginInPopup)}){window.open('/fixture-auth-popup');return}document.cookie='fixture_session=connected; Max-Age=3600; SameSite=Strict';ready()};
  root.querySelector('input').onchange=e=>{const img=new Image();img.src=URL.createObjectURL(e.target.files[0]);document.querySelector('#attachments').appendChild(img)};
  stop.onclick=()=>{stop.style.display='none';fetch('/stop')};
  if(${state.initialMode !== 'inert'})editor.onkeydown=async e=>{if(e.key!=='Enter')return;e.preventDefault();const prompt=editor.tagName==='TEXTAREA'?editor.value:editor.innerText;const user=document.createElement('div');user.setAttribute('data-message-item','');user.setAttribute('data-message-role','user');user.textContent=prompt;history.appendChild(user);if(editor.tagName==='TEXTAREA')editor.value='';else editor.replaceChildren();const attached=root.querySelectorAll('img').length;document.querySelector('#attachments').replaceChildren();root.querySelector('input').value='';stop.style.display='block';
    const mode=await(await fetch('/turn',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt,attached,path:location.pathname,viewport:{width:innerWidth,height:innerHeight},prehydrationValue:prehydration?.value||'',prehydrationFocus,prehydrationInputEvents,initialMode:${JSON.stringify(state.initialMode)}})})).json();
    if(mode.held) while(!(await(await fetch('/ready?id='+mode.id)).json()).ready) await new Promise(resolve=>setTimeout(resolve,80));
    if(mode.behavior==='slow')return;
    setTimeout(()=>{if(${Boolean(state.foreignTurn)}){const foreign=document.createElement('div');foreign.setAttribute('data-message-item','');foreign.setAttribute('data-message-role','user');foreign.textContent='A different user request after the current prompt';history.appendChild(foreign)}const reply=document.createElement('div');reply.setAttribute('data-message-item','');reply.setAttribute('data-message-role','assistant');
      if(mode.behavior==='video'){const video=document.createElement('video');video.src='/new.mp4';video.preload='metadata';reply.appendChild(video)}
      else if(mode.behavior==='image'){const img=document.createElement('img');if(mode.uniqueImages){const canvas=document.createElement('canvas');canvas.width=640;canvas.height=360;const ctx=canvas.getContext('2d');ctx.fillStyle='#172340';ctx.fillRect(0,0,640,360);ctx.fillStyle='#ffffff';ctx.font='32px sans-serif';ctx.fillText('FIXTURE IMAGE '+mode.id,30,180);img.src=canvas.toDataURL(${JSON.stringify(state.imageEncoding || 'image/png')});fetch('/capture',{method:'POST',body:JSON.stringify({id:mode.id,base64:img.src.split(',')[1]})})}else img.src='/new.png';reply.appendChild(img)}
      else if(mode.behavior==='error'){reply.innerHTML='<span data-testid="assistant-response-error-notice">429 quota exhausted</span>'}
      else reply.textContent='A new cinematic prompt, not old history.';
      history.appendChild(reply);stop.style.display='none';},100);
  };
  </script></body></html>`);
});

return { server: fixture, state, releaseAll() { for (const release of [...state.pending.values()]) release(); } };
}
