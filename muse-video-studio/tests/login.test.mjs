import { test } from 'node:test';
import assert from 'node:assert/strict';
import { _electron } from 'playwright-core';
import { createRequire } from 'node:module';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { createMuseFixture } from './fixtures/muse.mjs';

const require = createRequire(import.meta.url);
const root = fileURLToPath(new URL('..', import.meta.url));
const image = await readFile(new URL('../public/demo-image.png', import.meta.url));
const clip = await readFile(new URL('../public/demo.mp4', import.meta.url));
async function waitFor(predicate, message) {
  const deadline = Date.now() + 15000;
  while (!await predicate()) {
    if (Date.now() > deadline) throw new Error(message);
    await new Promise(resolve => setTimeout(resolve, 30));
  }
}

test('embedded login handles blank popups, email links and retry within one owned session', { timeout: 90000 }, async t => {
  const profile = await mkdtemp(path.join(os.tmpdir(), 'muse-login-test-'));
  const fixture = createMuseFixture({ image, clip });
  fixture.state.loginInPopup = 'blank';
  await new Promise(resolve => fixture.server.listen(0, '127.0.0.1', resolve));
  const service = `http://127.0.0.1:${fixture.server.address().port}/`;
  let desktop;
  try {
    desktop = await _electron.launch({ executablePath: require('electron'), args: [
      ...(process.env.MUSE_ELECTRON_TEST_NO_SANDBOX === '1' ? ['--no-sandbox', '--disable-gpu'] : []), path.join(root, 'desktop/main.mjs'),
    ], env: { ...process.env, MUSE_DESKTOP_TEST: '1', MUSE_FIXTURE_URL: service, MUSE_DESKTOP_DATA: profile, MUSE_TRANSPORT: 'browser', PORT: '0' }, timeout: 30000 });
    await desktop.firstWindow();
    let studio; let shell; let login; let popup;
    await waitFor(() => {
      const pages = desktop.context().pages();
      studio = pages.find(page => page.url().startsWith('http://127.0.0.1:') && !page.url().startsWith(service));
      shell = pages.find(page => page.url().endsWith('/desktop/shell.html'));
      return studio && shell;
    }, 'Studio did not open');
    await studio.getByRole('button', { name: 'Đăng nhập Muse trong tool', exact: true }).click();
    await waitFor(() => { login = desktop.context().pages().find(page => page.url() === service); return login; }, 'Muse login did not open');
    await t.test('blank authentication popups retain only the sandboxed Muse session', async () => {
    await login.getByRole('button', { name: 'Fixture login', exact: true }).click();
    await waitFor(async () => {
      popup = desktop.context().pages().find(page => page.url() === service + 'fixture-auth-popup');
      return popup || await login.locator('#popup-feedback').innerText();
    }, 'Blank popup did not redirect');
    assert.equal(await login.locator('#popup-feedback').innerText(), '', 'The tool blocked the blank window used by the login flow');
    assert.ok(popup, 'An owned authentication popup must open');
    assert.deepEqual(await popup.evaluate(() => [typeof window.require, typeof window.studioDesktop, typeof window.museTransport, typeof window.museEmailLogin]), ['undefined','undefined','undefined','undefined']);
    await popup.getByRole('button', { name: 'Finish fixture login', exact: true }).click();
    await waitFor(() => popup.isClosed(), 'Login popup did not close');
    await shell.getByRole('button', { name: '← Về Studio', exact: true }).click();
    await waitFor(async () => (await studio.evaluate(async () => (await fetch('/api/status')).json())).accounts[0].authenticated, 'Popup session was not verified');
    assert.equal(fixture.state.submitted.length, 0);
    });
    await t.test('the email link uses the same pending-login cookie and rejects other sites without leaking the link', async () => {
      fixture.state.emailLogin = true;
      await login.evaluate(() => { document.cookie = 'fixture_session=; Max-Age=0'; });
      await login.goto(service);
      await shell.getByRole('button',{name:'Đăng nhập Muse trong tool',exact:true}).click();
      await login.getByRole('button',{name:'Fixture login',exact:true}).click();
      assert.equal(await login.locator('#popup-feedback').innerText(),'Email sent');
      await shell.getByRole('button',{name:'Liên kết email',exact:true}).click();
      let form;
      await waitFor(()=>{form=desktop.context().pages().find(page=>page.url().endsWith('/desktop/email-login.html'));return form},'Email helper did not open');
      assert.deepEqual(await form.evaluate(()=>[typeof window.require,typeof window.museTransport,typeof window.studioDesktop]),['undefined','undefined','undefined']);
      assert.equal(await form.getByLabel('Liên kết đăng nhập Muse',{exact:true}).getAttribute('type'),'password');
      await form.getByLabel('Liên kết đăng nhập Muse',{exact:true}).fill('https://example.invalid/verify?ticket=fixture-private-value');
      await form.getByRole('button',{name:'Mở trong tool',exact:true}).click();
      await waitFor(async()=>(await form.locator('#feedback').innerText()).includes('Chỉ mở'),'Invalid site was not rejected');
      assert.equal((await form.locator('#feedback').innerText()).includes('fixture-private-value'),false);
      assert.equal(await form.getByLabel('Liên kết đăng nhập Muse',{exact:true}).inputValue(),'');
      assert.equal(login.url(),service);
      fixture.state.emailUsed=true;
      await form.getByLabel('Liên kết đăng nhập Muse',{exact:true}).fill(service+'fixture-email-verify?ticket=fixture-email-ticket');
      await form.getByRole('button',{name:'Mở trong tool',exact:true}).click();
      await waitFor(async()=>(await form.locator('#feedback').innerText()).includes('hết hạn'),'Consumed link was not reported');
      assert.equal(await form.getByLabel('Liên kết đăng nhập Muse',{exact:true}).inputValue(),'');
      assert.equal((await studio.evaluate(async()=>(await fetch('/api/status')).json())).accounts[0].authenticated,false);
      fixture.state.emailUsed=false;
      await form.getByLabel('Liên kết đăng nhập Muse',{exact:true}).fill(service+'fixture-email-verify?ticket=fixture-email-ticket');
      await form.getByRole('button',{name:'Mở trong tool',exact:true}).click();
      await waitFor(()=>form.isClosed(),'Email helper did not close after navigation');
      assert.equal(fixture.state.emailUsed,true,'The pending-login cookie must remain in the owned Muse partition');
      await shell.getByRole('button',{name:'← Về Studio',exact:true}).click();
      await waitFor(async()=>(await studio.evaluate(async()=>(await fetch('/api/status')).json())).accounts[0].authenticated,'Email session was not verified');
      assert.equal(fixture.state.submitted.length,0);
    });
    await t.test('reopening Muse retains the verified session and still blocks file URLs',async()=>{
      await shell.getByRole('button',{name:'Tải lại Muse',exact:true}).click();
      await waitFor(()=>login.url()===service,'Muse did not reopen');
      await waitFor(async()=>(await studio.evaluate(async()=>(await fetch('/api/status')).json())).accounts[0].authenticated,'Reload discarded login');
      assert.equal(await login.evaluate(()=>window.open('file:///tmp/muse-forbidden')===null),true);
      assert.deepEqual(await login.evaluate(()=>[typeof window.require,typeof window.museEmailLogin]),['undefined','undefined']);
      assert.equal(fixture.state.submitted.length,0);
    });
  } finally {
    await desktop?.close(); fixture.server.closeAllConnections();
    await new Promise(resolve => fixture.server.close(resolve));
    await rm(profile, { recursive: true, force: true });
  }
});
