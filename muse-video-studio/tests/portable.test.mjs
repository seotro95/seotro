import { test } from 'node:test';
import assert from 'node:assert/strict';
import { _electron } from 'playwright-core';
import { mkdtemp, readFile, rm, mkdir, readdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import os from 'node:os';
import { createMuseFixture } from './fixtures/muse.mjs';

const executablePath = process.env.MUSE_PORTABLE_EXECUTABLE;
if (!executablePath) throw new Error('Set MUSE_PORTABLE_EXECUTABLE to a prepared portable Linux executable.');
const image = await readFile(new URL('../public/demo-image.png', import.meta.url));
const clip = await readFile(new URL('../public/demo.mp4', import.meta.url));
const version = JSON.parse(await readFile(new URL('../package.json', import.meta.url), 'utf8')).version;
async function waitFor(predicate, timeout = 30000) {
  const deadline = Date.now() + timeout;
  while (!await predicate()) {
    if (Date.now() > deadline) throw new Error('Portable app did not reach the expected state.');
    await new Promise(resolve => setTimeout(resolve, 40));
  }
}
async function collectDownloads(desktop, directory) {
  await desktop.evaluate(({ session }, directory) => {
    globalThis.fixtureDownloads = [];
    session.fromPartition('persist:studio').on('will-download', (_event, item) => {
      const filename = item.getFilename();
      item.setSavePath(`${directory}/${filename}`);
      item.once('done', (_event, state) => globalThis.fixtureDownloads.push({ filename, state }));
    });
  }, directory);
}

test('portable app submits ten independent scenes concurrently, views images and saves numbered folders without an old install', { timeout: 180000 }, async () => {
  const profile = await mkdtemp(path.join(os.tmpdir(), 'muse-portable-test-'));
  const fixture = createMuseFixture({ image, clip });
  Object.assign(fixture.state, { otpLogin: true, rejectAuthChecksDuringOtp: true, prehydrationInput: true, richComposer: true, initialMode: 'functional', behavior: 'image', oldConversation: false, newChat: true, chatRoutes: true, sharedHistory: true, uniqueImages: true, imageEncoding: 'image/webp' });
  await new Promise(resolve => fixture.server.listen(0, '127.0.0.1', resolve));
  const service = `http://127.0.0.1:${fixture.server.address().port}/`;
  const env = { ...process.env, PATH: '/no-external-runtime', NODE_PATH: '', MUSE_DESKTOP_TEST: '1', MUSE_FIXTURE_URL: service, MUSE_DESKTOP_DATA: profile, MUSE_TRANSPORT: 'browser' };
  delete env.PORT;
  let desktop;
  try {
    desktop = await _electron.launch({ executablePath, args: process.env.MUSE_ELECTRON_TEST_NO_SANDBOX === '1' ? ['--no-sandbox', '--disable-gpu'] : [], env, timeout: 30000 });
    console.log('Portable stage: launch');
    await desktop.firstWindow();
    assert.equal(await desktop.evaluate(({ app }) => app.isPackaged), true);
    assert.equal(await desktop.evaluate(({ app }) => app.getVersion()), version);
    let studio, shell;
    await waitFor(() => {
      studio = desktop.context().pages().find(page => page.url().startsWith('http://127.0.0.1:') && !page.url().startsWith(service));
      shell = desktop.context().pages().find(page => page.url().endsWith('/desktop/shell.html'));
      return studio && shell;
    });
    assert.notEqual(new URL(studio.url()).port, '8788');
    assert.match(await shell.locator('nav strong').innerText(), new RegExp(version.replaceAll('.', '\\.')));
    await studio.getByRole('button', { name: 'Đăng nhập Muse trong tool', exact: true }).click();
    let login;
    await waitFor(() => { login = desktop.context().pages().find(page => page.url() === service); return login; });
    await login.getByLabel('Email đăng nhập',{exact:true}).fill('fixture@example.invalid');
    await login.getByRole('button',{name:'Gửi mã',exact:true}).click();
    await login.getByLabel('Mã xác nhận',{exact:true}).fill('246810');
    await login.getByRole('button',{name:'Xác nhận mã',exact:true}).click();
    await waitFor(()=>fixture.state.otpUsed);
    assert.equal(fixture.state.otpChecksDuringPending||0,0,'Packaged app must not interfere with a pending OTP challenge');
    await shell.getByRole('button', { name: '← Về Studio', exact: true }).click();
    await waitFor(async () => (await studio.locator('.connection-pill').innerText()).includes('Đã xác minh'));
    assert.equal(fixture.state.submitted.length, 0);
    console.log('Portable stage: verified');
    await studio.getByLabel('Số luồng:',{exact:true}).selectOption('10');
    try { await waitFor(async()=> (await studio.getByLabel('Số luồng:',{exact:true}).inputValue())==='10',90000); } catch(error) { console.error('Parallel selection',JSON.stringify({feedback:await studio.locator('.composer-feedback').allTextContents(),status:await studio.evaluate(async()=>(await fetch('/api/status')).json())}));throw error; }
    console.log('Portable stage: parallel-selected');
    fixture.state.hold=true;
    await studio.getByRole('button', { name: 'Tạo ảnh hàng loạt', exact: true }).click();
    await studio.getByRole('button', { name: 'TẠO 10 ẢNH', exact: true }).click();
    await waitFor(()=>fixture.state.pending.size===10,60000);
    console.log('Portable stage: pending-ten');
    assert.equal(fixture.state.peak,10,'Ten requests must overlap before any result is released');
    assert.equal(new Set(fixture.state.submitted.map(request=>request.path)).size,10);
    await waitFor(async()=> (await studio.evaluate(async()=>(await fetch('/api/status')).json())).workerProgress.filter(stage=>stage.active&&stage.submitted).length===10);
    await studio.getByRole('button',{name:'Tạo video',exact:true}).click();
    await studio.getByLabel('Chất lượng',{exact:true}).selectOption('1080p');
    assert.equal(await studio.locator('.status-badge.running').count(),10);
    await studio.getByRole('button',{name:'Tạo ảnh hàng loạt',exact:true}).click();
    fixture.releaseAll();fixture.state.hold=false;

    await waitFor(async () => {
      const errors = await studio.locator('.scene-error pre').allTextContents();
      if (errors.length) throw new Error('Portable batch failed: ' + errors.join('\n'));
      return await studio.locator('.generated-image').count() === 10;
    }, 60000);
    console.log('Portable stage: results-ten');
    assert.equal(fixture.state.submitted.length, 10);
    assert.equal(fixture.state.peak, 10);
    assert.equal(await studio.locator('.scene-error').count(), 0);
    assert.equal(fixture.state.submitted[0].initialMode, 'functional');
    assert.equal(fixture.state.submitted[0].authenticated, true);
    assert.match(fixture.state.submitted[0].prompt, /studio-request-/);
    const pagesBefore=desktop.context().pages().length;
    await studio.getByRole('button',{name:'Xem ảnh cảnh 1',exact:true}).click();
    const viewer=studio.getByRole('dialog',{name:'Xem ảnh cảnh 1',exact:true});
    await waitFor(async()=> viewer.locator('img').evaluate(image=>image.complete&&image.naturalWidth===640));
    assert.equal(desktop.context().pages().length,pagesBefore,'Image viewing must not open a blank popup');
    await viewer.getByRole('button',{name:'Đóng',exact:true}).click();
    const downloads = path.join(profile, 'downloads');
    await mkdir(downloads);
    const exportsRoot=path.join(profile,'exports');await mkdir(exportsRoot);
    await desktop.evaluate(({dialog,shell},directory)=>{
      globalThis.directoryChoices=0;globalThis.lastFolder=null;
      dialog.showOpenDialog=async()=>{globalThis.directoryChoices++;return {canceled:false,filePaths:[directory]}};
      shell.openPath=async folder=>{globalThis.lastFolder=folder;return ''};
    },exportsRoot);

    await collectDownloads(desktop, downloads);
    await studio.evaluate(() => new Promise((resolve,reject) => {
      const request=indexedDB.open('muse-studio-downloads-v1',1);
      request.onupgradeneeded=()=>request.result.createObjectStore('counters');
      request.onerror=()=>reject(request.error);
      request.onsuccess=()=>{
        const db=request.result;const tx=db.transaction('counters','readwrite');
        tx.objectStore('counters').put({last:'999',namespace:'b'.repeat(32)},'sequence');
        tx.oncomplete=()=>{db.close();resolve()};tx.onerror=()=>{db.close();reject(tx.error)};
      };
    }));
    await studio.getByRole('button', { name: 'Tải cảnh 1', exact: true }).click();
    await waitFor(async () => await desktop.evaluate(() => globalThis.fixtureDownloads.length) === 1);
    await studio.getByRole('button', { name: 'Tải tất cả (10/10)', exact: true }).click();
    await waitFor(async()=>Boolean(await desktop.evaluate(()=>globalThis.lastFolder)));
    const saved = await desktop.evaluate(() => globalThis.fixtureDownloads);
    assert.equal(saved.length,1,'Saving a folder must not start a ZIP download');
    assert.equal(saved[0].state,'completed');
    assert.equal(saved[0].filename, `image-001000-scene-01-${'b'.repeat(32)}.png`);
    console.log('Portable stage: folder-saved');
    const folder=await desktop.evaluate(()=>globalThis.lastFolder);
    assert.equal(await desktop.evaluate(()=>globalThis.directoryChoices),1);
    const names=(await readdir(folder)).sort();
    assert.deepEqual(names,Array.from({length:10},(_,index)=>`image-${String(index+1001).padStart(6,'0')}-scene-${String(index+1).padStart(2,'0')}-${'b'.repeat(32)}.png`));
    const archive=await Promise.all(names.map(async name=>({name,bytes:await readFile(path.join(folder,name))})));
    const hashes=new Set();
    const single = await readFile(path.join(downloads, saved[0].filename));
    for (const { bytes, name } of [{ bytes: single, name: 'single.png' }, ...archive]) {
      assert.ok(bytes.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10])));
      const dimensions = await studio.evaluate(base64 => new Promise((resolve, reject) => {
        const image = new Image(); image.onload = () => resolve([image.naturalWidth, image.naturalHeight]); image.onerror = reject; image.src = 'data:image/png;base64,' + base64;
      }), bytes.toString('base64'));
      assert.deepEqual(dimensions, [640, 360]);
      if (name !== 'single.png') hashes.add(createHash('sha256').update(bytes).digest('hex'));
    }
    assert.equal(hashes.size, 10);
    const studioURL = studio.url();
    const savedPrompt = 'A script saved by the complete portable app';
    await studio.getByLabel('Kịch bản cảnh 2', { exact: true }).fill(savedPrompt);
    await desktop.close(); desktop = null;
    desktop = await _electron.launch({ executablePath, args: process.env.MUSE_ELECTRON_TEST_NO_SANDBOX === '1' ? ['--no-sandbox', '--disable-gpu'] : [], env, timeout: 30000 });
    console.log('Portable stage: launch');
    await desktop.firstWindow();
    await waitFor(() => { studio = desktop.context().pages().find(page => page.url() === studioURL); return studio; });
    console.log('Portable stage: reopened');
    assert.equal(await studio.getByLabel('Kịch bản cảnh 2', { exact: true }).inputValue(), savedPrompt);
    await waitFor(async () => await studio.locator('.generated-image').count() === 9);
    assert.equal(await studio.locator('.history-entry').count(), 10, 'Generated files must persist across a full executable restart');
    assert.equal(fixture.state.submitted.length, 10, 'Restoring saved results must not render again');
    await collectDownloads(desktop, downloads);
    await studio.getByRole('button',{name:'Tải cảnh 1',exact:true}).click();
    await waitFor(async()=>await desktop.evaluate(()=>globalThis.fixtureDownloads.length)===1);
    const resumed=await desktop.evaluate(()=>globalThis.fixtureDownloads[0]);
    assert.equal(resumed.state,'completed');
    assert.equal(resumed.filename,`image-001011-scene-01-${'b'.repeat(32)}.png`);
    assert.equal((await readdir(downloads)).length,2,'Reopening must continue the counter without overwriting any file');
    assert.equal(fixture.state.submitted.length,10);
    await desktop.evaluate(({dialog,shell})=>{
      globalThis.lastFolder=null;
      dialog.showOpenDialog=async()=>{throw new Error('The selected folder should be remembered')};
      shell.openPath=async folder=>{globalThis.lastFolder=folder;return ''};
    });
    await studio.getByRole('button',{name:'Tải tất cả (9/10)',exact:true}).click();
    await waitFor(async()=>Boolean(await desktop.evaluate(()=>globalThis.lastFolder)));
    const resumedFolder=await desktop.evaluate(()=>globalThis.lastFolder);
    assert.notEqual(resumedFolder,folder);
    assert.equal((await readdir(resumedFolder)).length,9);
    assert.equal((await readdir(folder)).length,10);
    assert.equal((await readdir(exportsRoot)).length,2);
    assert.equal(fixture.state.submitted.length,10);
  } finally {
    await desktop?.close();
    fixture.server.closeAllConnections();
    await new Promise(resolve => fixture.server.close(resolve));
    await rm(profile, { recursive: true, force: true });
  }
});
