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
    await new Promise(resolve => setTimeout(resolve,30));
  }
}

test('email OTP works in the embedded Muse page without reading or replacing the code', { timeout: 60000 }, async t => {
  const profile = await mkdtemp(path.join(os.tmpdir(),'muse-otp-test-'));
  const fixture = createMuseFixture({ image, clip });
  fixture.state.otpLogin = true;
  fixture.state.rejectAuthChecksDuringOtp = true;
  await new Promise(resolve => fixture.server.listen(0,'127.0.0.1',resolve));
  const service = `http://127.0.0.1:${fixture.server.address().port}/`;
  let desktop;
  try {
    desktop = await _electron.launch({ executablePath: require('electron'), args: [
      ...(process.env.MUSE_ELECTRON_TEST_NO_SANDBOX==='1'?['--no-sandbox','--disable-gpu']:[]),path.join(root,'desktop/main.mjs'),
    ], env: { ...process.env,MUSE_DESKTOP_TEST:'1',MUSE_FIXTURE_URL:service,MUSE_DESKTOP_DATA:profile,MUSE_TRANSPORT:'browser',PORT:'0' },timeout:30000 });
    await desktop.firstWindow();
    let studio;let shell;let login;
    await waitFor(()=>{
      const pages=desktop.context().pages();
      studio=pages.find(page=>page.url().startsWith('http://127.0.0.1:')&&!page.url().startsWith(service));
      shell=pages.find(page=>page.url().endsWith('/desktop/shell.html'));
      return studio&&shell;
    },'Studio did not open');
    await studio.getByRole('button',{name:'Đăng nhập Muse trong tool',exact:true}).click();
    await waitFor(()=>{login=desktop.context().pages().find(page=>page.url()===service);return login},'Login did not open');
    await t.test('requesting a code keeps the same challenge when returning between Studio and Muse',async()=>{
      await login.getByLabel('Email đăng nhập',{exact:true}).fill('fixture@example.invalid');
      await login.getByRole('button',{name:'Gửi mã',exact:true}).click();
      await waitFor(()=>fixture.state.otpRequests===1,'OTP was not requested');
      await shell.getByRole('button',{name:'← Về Studio',exact:true}).click();
      await shell.getByRole('button',{name:'Đăng nhập Muse trong tool',exact:true}).click();
      assert.equal(await login.getByLabel('Email đăng nhập',{exact:true}).inputValue(),'fixture@example.invalid');
      assert.equal(await login.getByLabel('Mã xác nhận',{exact:true}).isVisible(),true);
      assert.equal(fixture.state.otpRequests,1,'Tool must not reload the form or request a second code');
      assert.equal((await studio.evaluate(async()=>(await fetch('/api/status')).json())).accounts[0].authenticated,false);
      assert.equal(fixture.state.otpChecksDuringPending||0,0,'The tool must not send extra authentication POSTs while an OTP challenge is visible');
    });
    await t.test('copying a passive login report neither touches the OTP challenge nor includes secrets',async()=>{
      await desktop.evaluate(({dialog})=>{dialog.showMessageBox=async()=>({response:1,checkboxChecked:false})});
      await shell.getByRole('button',{name:'Chẩn đoán đăng nhập',exact:true}).click();
      let text;
      await waitFor(async()=>{text=await desktop.evaluate(({clipboard})=>clipboard.readText());return text.startsWith('{')},'Login report was not copied');
      const report=JSON.parse(text);
      assert.equal(report.state,'awaiting_code');
      assert.equal(report.verified,false);
      for(const secret of ['246810','135791','fixture@example.invalid',fixture.state.otpChallenge])assert.equal(text.includes(secret),false);
      assert.equal(fixture.state.otpChecksDuringPending||0,0);
    });
    await t.test('only the newest code is accepted; keyboard and paste reach the owned Muse input',async()=>{
      await login.getByRole('button',{name:'Gửi mã',exact:true}).click();
      await waitFor(()=>fixture.state.otpRequests===2,'Resend did not finish');
      await login.getByLabel('Mã xác nhận',{exact:true}).click();
      await login.keyboard.type('246810');
      await login.getByRole('button',{name:'Xác nhận mã',exact:true}).click();
      await waitFor(async()=>(await login.locator('#otp-feedback').innerText()).includes('hết hạn'),'Old code was not rejected');
      assert.equal((await studio.evaluate(async()=>(await fetch('/api/status')).json())).accounts[0].authenticated,false);
      await login.getByLabel('Mã xác nhận',{exact:true}).fill('');
      await desktop.evaluate(({clipboard})=>clipboard.writeText('135791'));
      await login.getByLabel('Mã xác nhận',{exact:true}).click();
      await login.keyboard.press('Control+V');
      assert.equal(await login.getByLabel('Mã xác nhận',{exact:true}).inputValue(),'135791');
      await login.getByRole('button',{name:'Xác nhận mã',exact:true}).click();
      await waitFor(()=>fixture.state.otpUsed,'New code was not verified');
      await shell.getByRole('button',{name:'← Về Studio',exact:true}).click();
      await waitFor(async()=>(await studio.evaluate(async()=>(await fetch('/api/status')).json())).accounts[0].authenticated,'Studio did not verify the OTP session');
      assert.equal(fixture.state.submitted.length,0);
      assert.deepEqual(await login.evaluate(()=>[typeof window.require,typeof window.museTransport]),['undefined','undefined']);
    });
  } finally {
    await desktop?.close();fixture.server.closeAllConnections();
    await new Promise(resolve=>fixture.server.close(resolve));
    await rm(profile,{recursive:true,force:true});
  }
});
