import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { existsSync } from 'node:fs';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { MuseBrowser } from '../muse-browser.mjs';

const executablePath = process.env.CHROMIUM_PATH;
if (!executablePath) throw new Error('Set CHROMIUM_PATH to a local Chromium/Chrome executable to run the browser bridge fixture checks.');
const image = await readFile(new URL('../public/demo-image.png', import.meta.url));
const clip = await readFile(new URL('../public/demo.mp4', import.meta.url));
const png = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aO1sAAAAASUVORK5CYII=';
let behavior = 'video';
let submitted = [];
let stops = 0;
const fixture = http.createServer(async (req, res) => {
  if (req.url === '/api/auth/check') { res.setHeader('Content-Type', 'application/json'); return res.end(JSON.stringify({ ok: /fixture_session=connected/.test(req.headers.cookie || '') })); }
  if (req.url === '/turn') { let text = ''; for await (const chunk of req) text += chunk; submitted.push(JSON.parse(text)); res.setHeader('Content-Type', 'application/json'); return res.end(JSON.stringify({ behavior })); }
  if (req.url === '/stop') { stops++; return res.end('ok'); }
  if (req.url?.endsWith('.png')) { res.setHeader('Content-Type', 'image/png'); return res.end(image); }
  if (req.url?.endsWith('.mp4')) { res.setHeader('Content-Type', 'video/mp4'); return res.end(clip); }
  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.end(`<!doctype html><html><body>
  <header><span data-testid="token-balance">Tokens remaining: 1,234</span></header><button id="login">Fixture login</button>
  <div id="history"><div data-message-item data-message-role="assistant">OLD RESPONSE Tokens remaining: 999999<img src="/old.png"><video src="/old.mp4" preload="metadata"></video></div></div>
  <div data-hatch-composer-root style="display:none"><textarea></textarea><input type="file" accept="image/*"><span id="attachments"></span></div>
  <button data-testid="hatch-composer-stop-button" style="display:none">Stop</button>
  <script>
  const root=document.querySelector('[data-hatch-composer-root]');const editor=root.querySelector('textarea');const history=document.querySelector('#history');const stop=document.querySelector('[data-testid="hatch-composer-stop-button"]');
  function ready(){root.style.display=document.cookie.includes('fixture_session=connected')?'block':'none'};ready();
  document.querySelector('#login').onclick=()=>{document.cookie='fixture_session=connected; Max-Age=3600; SameSite=Strict';ready()};
  root.querySelector('input').onchange=e=>{const img=new Image();img.src=URL.createObjectURL(e.target.files[0]);document.querySelector('#attachments').appendChild(img)};
  stop.onclick=()=>{stop.style.display='none';fetch('/stop')};
  editor.onkeydown=async e=>{if(e.key!=='Enter')return;e.preventDefault();const prompt=editor.value;const user=document.createElement('div');user.setAttribute('data-message-item','');user.setAttribute('data-message-role','user');user.textContent=prompt;history.appendChild(user);editor.value='';const attached=root.querySelectorAll('img').length;document.querySelector('#attachments').replaceChildren();root.querySelector('input').value='';stop.style.display='block';
    const mode=await(await fetch('/turn',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt,attached})})).json();
    if(mode.behavior==='slow')return;
    setTimeout(()=>{const reply=document.createElement('div');reply.setAttribute('data-message-item','');reply.setAttribute('data-message-role','assistant');
      if(mode.behavior==='video'){const video=document.createElement('video');video.src='/new.mp4';video.preload='metadata';reply.appendChild(video)}
      else if(mode.behavior==='image'){const img=document.createElement('img');img.src='/new.png';reply.appendChild(img)}
      else if(mode.behavior==='error'){reply.innerHTML='<span data-testid="assistant-response-error-notice">429 quota exhausted</span>'}
      else reply.textContent='A new cinematic prompt, not old history.';
      history.appendChild(reply);stop.style.display='none';},100);
  };
  </script></body></html>`);
});

test('owned browser bridge against local Muse-shaped pages (not live Muse)', async t => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'muse-bridge-test-'));
  await new Promise(resolve => fixture.listen(0, '127.0.0.1', resolve));
  const driver = new MuseBrowser({ profileRoot: root, serviceURL: `http://127.0.0.1:${fixture.address().port}/`, launchOptions: { executablePath, headless: true }, pollMs: 30, quietMs: 80, timeoutMs: 2500 });
  const data = { accountId: 1, modelDisplayName: 'Omni 1.1 Flash', durationSeconds: 4, aspectRatio: '16:9', resolution: '360p', prompt: 'A forest at sunrise' };
  try {
    await t.test('does not infer authentication from the existence of a browser profile', async () => {
      const accounts = await driver.connect(1);
      assert.equal(accounts[0].authenticated, false);
      assert.equal(accounts[0].state, 'login_open');
      await assert.rejects(driver.generateVideo(data, new AbortController().signal), /MUSE_LOGIN_REQUIRED/);
      assert.equal(submitted.length, 0);
      await driver.active.page.getByText('Fixture login', { exact: true }).click();
      await driver.refreshActive();
      assert.equal(driver.snapshot()[0].authenticated, true);
    });
    await t.test('submits the reference and returns the new playable video with observed metadata', async () => {
      behavior = 'video';
      const result = await driver.generateVideo({ ...data, referenceImage: { base64: png, mimeType: 'image/png' } }, new AbortController().signal);
      assert.equal(result.base64, clip.toString('base64'));
      assert.equal(result.mimeType, 'video/mp4');
      assert.equal(result.metadata.width, 640); assert.equal(result.metadata.height, 360);
      assert.ok(Math.abs(result.metadata.duration - 4) < 0.2);
      assert.equal(submitted.at(-1).attached, 1);
      assert.match(submitted.at(-1).prompt, /A forest at sunrise/);
      assert.match(submitted.at(-1).prompt, /Requested model: Omni 1.1 Flash/);
    });
    await t.test('reads real labelled account balance and never copies a token number from chat', async () => {
      await driver.refreshActive();
      assert.equal(driver.snapshot()[0].balance.valueText, '1,234');
      assert.equal(driver.snapshot()[0].balance.unit, 'token');
      await driver.active.page.locator('[data-testid="token-balance"]').evaluate(el => el.textContent = 'Tokens remaining: 0');
      await driver.refreshActive(); assert.equal(driver.snapshot()[0].balance.valueText, '0');
      await driver.active.page.locator('[data-testid="token-balance"]').evaluate(el => el.remove());
      await driver.refreshActive(); assert.equal(driver.snapshot()[0].balance, null);
    });
    await t.test('generates images with measured size and independent prompts, then animates an image', async () => {
      behavior = 'image';
      const referenceImage = { base64: png, mimeType: 'image/png' };
      const locked = await driver.generateImage({ accountId: 1, prompt: 'Portrait in a forest', aspectRatio: '16:9', resolution: '4k', characterLock: true, referenceImage }, new AbortController().signal);
      assert.equal(locked.mimeType, 'image/png'); assert.equal(locked.base64, image.toString('base64'));
      assert.equal(locked.metadata.width, 640); assert.equal(locked.metadata.height, 360);
      assert.equal(submitted.at(-1).attached, 1); assert.match(submitted.at(-1).prompt, /3840x2160/);
      await driver.generateImage({ accountId: 1, prompt: 'A different person at sea', aspectRatio: '9:16', resolution: '2k', characterLock: false, referenceImage }, new AbortController().signal);
      assert.equal(submitted.at(-1).attached, 0); assert.match(submitted.at(-1).prompt, /A different person at sea/);
      assert.match(submitted.at(-1).prompt, /Do not reuse characters/);
      behavior = 'video';
      await driver.generateVideo({ ...data, sourceMode: 'image', characterLock: false, resolution: '1080p', referenceImage: { base64: locked.base64, mimeType: locked.mimeType } }, new AbortController().signal);
      assert.equal(submitted.at(-1).attached, 1); assert.match(submitted.at(-1).prompt, /starting frame/);
      assert.match(submitted.at(-1).prompt, /1080p/);
    });
    await t.test('reads only the new text turn and preserves an unrelated unsent draft', async () => {
      behavior = 'text';
      const result = await driver.generateText({ accountId: 1, prompt: 'Enhance the scene' }, new AbortController().signal);
      assert.equal(result.text, 'A new cinematic prompt, not old history.');
      await driver.active.page.locator('textarea').fill('My private unsent draft');
      const count = submitted.length;
      await assert.rejects(driver.generateText({ accountId: 1, prompt: 'Do not send' }, new AbortController().signal), /MUSE_DRAFT_EXISTS/);
      await assert.rejects(driver.connect(2), /ACCOUNT_INVALID/);
      assert.equal(driver.active.id, 1);
      assert.equal(submitted.length, count);
      assert.equal(await driver.active.page.locator('textarea').inputValue(), 'My private unsent draft');
      await driver.active.page.locator('textarea').fill('');
    });
    await t.test('uses only one profile, rejects other accounts and reopens its saved session', async () => {
      assert.equal(driver.snapshot().length, 1);
      await assert.rejects(driver.connect(2), /ACCOUNT_INVALID/);
      assert.equal(driver.active.id, 1);
      assert.equal(existsSync(path.join(root, 'slot-02')), false);
      await driver.close();
      assert.equal(driver.snapshot()[0].state, 'session_saved');
      await driver.connect();
      assert.equal(driver.snapshot()[0].authenticated, true);
      assert.equal(driver.snapshot().length, 1);
    });
    await t.test('does not return old videos when the new response has no video', async () => {
      behavior = 'text'; driver.timeoutMs = 500;
      await assert.rejects(driver.generateVideo(data, new AbortController().signal), /MUSE_TIMEOUT/);
      driver.timeoutMs = 2500;
    });
    await t.test('preserves provider errors and sends Stop when locally cancelled', async () => {
      behavior = 'error';
      await assert.rejects(driver.generateVideo(data, new AbortController().signal), /429 quota exhausted/);
      behavior = 'slow';
      const control = new AbortController();
      const task = driver.generateVideo(data, control.signal);
      const timer = setTimeout(() => control.abort(), 350);
      await assert.rejects(task, error => error.name === 'AbortError');
      clearTimeout(timer);
      assert.equal(stops, 1);
    });
    await t.test('checks authentication again before every send, including an expired saved session', async () => {
      await driver.active.page.evaluate(() => { document.cookie = 'fixture_session=; Max-Age=0'; });
      const count = submitted.length;
      await assert.rejects(driver.generateVideo(data, new AbortController().signal), /MUSE_LOGIN_REQUIRED/);
      assert.equal(submitted.length, count);
      assert.equal(driver.snapshot()[0].authenticated, false);
    });
  } finally { await driver.close(); fixture.closeAllConnections(); await new Promise(resolve => fixture.close(resolve)); await rm(root, { recursive: true, force: true }); }
});
