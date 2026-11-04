import http from 'node:http';

export function createMuseFixture({ image, clip }) {
const state = { behavior: 'video', submitted: [], stops: 0, hold: false, peak: 0, pending: new Map(), released: new Set(), outputs: new Map(), uniqueImages: false, oldConversation: false, newChat: true, prehydrationInput: false, richComposer: false, hydrationDelayMs: 0, authStatus: 200, loginInPopup: false, composerLayout: 'hatch', landingOnly: false, editorLabel: 'Message', chatPath: '', frameComposer: false };
const fixture = http.createServer(async (req, res) => {
  if (req.url === '/api/auth/check') { res.statusCode = state.authStatus; res.setHeader('Content-Type', 'application/json'); return res.end(JSON.stringify({ ok: /fixture_session=connected/.test(req.headers.cookie || '') })); }
  if (req.url === '/fixture-auth-popup') { res.setHeader('Content-Type', 'text/html; charset=utf-8'); return res.end(`<html><button id="finish">Finish fixture login</button><script>document.querySelector('#finish').onclick=()=>{document.cookie='fixture_session=connected; Max-Age=3600; SameSite=Strict';window.close()}</script></html>`); }
  if (req.url === '/turn') {
    let text = ''; for await (const chunk of req) text += chunk;
    const request = { ...JSON.parse(text), id: state.submitted.length + 1, authenticated: /fixture_session=connected/.test(req.headers.cookie || '') };
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
  if (req.url?.endsWith('.png')) { res.setHeader('Content-Type', 'image/png'); return res.end(image); }
  if (req.url?.endsWith('.mp4')) { res.setHeader('Content-Type', 'video/mp4'); return res.end(clip); }
  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  const requestPath = new URL(req.url, 'http://127.0.0.1').pathname;
  if (state.chatPath && requestPath === '/') return res.end('<!doctype html><html><body><h1>Fixture dashboard without chat</h1></body></html>');
  if (state.frameComposer && requestPath !== '/composer-frame') return res.end('<!doctype html><html><body><iframe title="Muse chat" src="/composer-frame" style="width:100%;height:900px;border:0"></iframe></body></html>');
  const rootTag = state.composerLayout === 'hatch' ? 'div' : 'form';
  res.end(`<!doctype html><html><body>
  <header><span data-testid="token-balance">Tokens remaining: 1,234</span></header><button id="login">Fixture login</button>
  ${state.newChat ? '<button id="new-chat">New chat</button>' : ''}<div id="history">${state.oldConversation ? '<div data-message-item data-message-role="user">Old thread</div>' : ''}<div data-message-item data-message-role="assistant">OLD RESPONSE Tokens remaining: 999999<img src="/old.png"><video src="/old.mp4" preload="metadata"></video></div></div>
  <${rootTag} id="fixture-composer" ${state.composerLayout === 'hatch' ? 'data-hatch-composer-root' : ''} style="display:none">${state.prehydrationInput ? `<textarea rows="1" aria-label="Message" placeholder="Message" data-hatch-composer-prehydration-input="true" style="display:${state.hydrationDelayMs ? 'block' : 'none'}"></textarea>` : ''}${state.richComposer ? `<div id="fixture-editor" contenteditable="true" data-lexical-editor="true" role="textbox" aria-label="${state.editorLabel}" style="display:${state.hydrationDelayMs ? 'none' : 'block'}"></div>` : `<textarea id="fixture-editor" aria-label="${state.editorLabel}"></textarea>`}${state.composerLayout === 'ambiguous' ? '<textarea aria-label="Message" id="other-editor"></textarea>' : ''}<input type="file" accept="image/*"><span id="attachments"></span></${rootTag}>
  <button data-testid="hatch-composer-stop-button" style="display:none">Stop</button>
  <script>
  const root=document.querySelector('#fixture-composer');const editor=root.querySelector('#fixture-editor');const history=document.querySelector('#history');const stop=document.querySelector('[data-testid="hatch-composer-stop-button"]');
  if(${state.hydrationDelayMs})setTimeout(()=>{root.querySelector('[data-hatch-composer-prehydration-input]')?.style.setProperty('display','none');editor.style.display='block'},${state.hydrationDelayMs});
  let conversationOpen=${!state.landingOnly};
  function ready(){root.style.display=document.cookie.includes('fixture_session=connected')&&conversationOpen?'block':'none'};ready();
  document.querySelector('#new-chat')?.addEventListener('click',()=>{history.replaceChildren();conversationOpen=true;ready()});
  document.querySelector('#login').onclick=()=>{if(${state.loginInPopup}){window.open('/fixture-auth-popup');return}document.cookie='fixture_session=connected; Max-Age=3600; SameSite=Strict';ready()};
  root.querySelector('input').onchange=e=>{const img=new Image();img.src=URL.createObjectURL(e.target.files[0]);document.querySelector('#attachments').appendChild(img)};
  stop.onclick=()=>{stop.style.display='none';fetch('/stop')};
  editor.onkeydown=async e=>{if(e.key!=='Enter')return;e.preventDefault();const prompt=editor.tagName==='TEXTAREA'?editor.value:editor.innerText;const user=document.createElement('div');user.setAttribute('data-message-item','');user.setAttribute('data-message-role','user');user.textContent=prompt;history.appendChild(user);if(editor.tagName==='TEXTAREA')editor.value='';else editor.replaceChildren();const attached=root.querySelectorAll('img').length;document.querySelector('#attachments').replaceChildren();root.querySelector('input').value='';stop.style.display='block';
    const mode=await(await fetch('/turn',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt,attached,path:location.pathname,viewport:{width:innerWidth,height:innerHeight},prehydrationValue:root.querySelector('[data-hatch-composer-prehydration-input]')?.value||''})})).json();
    if(mode.held) while(!(await(await fetch('/ready?id='+mode.id)).json()).ready) await new Promise(resolve=>setTimeout(resolve,80));
    if(mode.behavior==='slow')return;
    setTimeout(()=>{const reply=document.createElement('div');reply.setAttribute('data-message-item','');reply.setAttribute('data-message-role','assistant');
      if(mode.behavior==='video'){const video=document.createElement('video');video.src='/new.mp4';video.preload='metadata';reply.appendChild(video)}
      else if(mode.behavior==='image'){const img=document.createElement('img');if(mode.uniqueImages){const canvas=document.createElement('canvas');canvas.width=640;canvas.height=360;const ctx=canvas.getContext('2d');ctx.fillStyle='#172340';ctx.fillRect(0,0,640,360);ctx.fillStyle='#ffffff';ctx.font='32px sans-serif';ctx.fillText('FIXTURE IMAGE '+mode.id,30,180);img.src=canvas.toDataURL('image/png');fetch('/capture',{method:'POST',body:JSON.stringify({id:mode.id,base64:img.src.split(',')[1]})})}else img.src='/new.png';reply.appendChild(img)}
      else if(mode.behavior==='error'){reply.innerHTML='<span data-testid="assistant-response-error-notice">429 quota exhausted</span>'}
      else reply.textContent='A new cinematic prompt, not old history.';
      history.appendChild(reply);stop.style.display='none';},100);
  };
  </script></body></html>`);
});

return { server: fixture, state, releaseAll() { for (const release of [...state.pending.values()]) release(); } };
}
