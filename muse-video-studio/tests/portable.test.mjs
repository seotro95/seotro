import { test } from 'node:test';
import assert from 'node:assert/strict';
import { _electron } from 'playwright-core';
import { mkdtemp, readFile, rm, mkdir, readdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import os from 'node:os';
import { createMuseFixture } from './fixtures/muse.mjs';
import { readZip } from './fixtures/read-zip.mjs';

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

test('portable app queues ten scenes in one persistent conversation, exports real PNG files and needs no old install', { timeout: 120000 }, async () => {
  const profile = await mkdtemp(path.join(os.tmpdir(), 'muse-portable-test-'));
  const fixture = createMuseFixture({ image, clip });
  Object.assign(fixture.state, { prehydrationInput: true, richComposer: true, initialMode: 'functional', behavior: 'image', oldConversation: true, newChat: false, sharedHistory: true, uniqueImages: true, imageEncoding: 'image/webp' });
  await new Promise(resolve => fixture.server.listen(0, '127.0.0.1', resolve));
  const service = `http://127.0.0.1:${fixture.server.address().port}/`;
  const env = { ...process.env, PATH: '/no-external-runtime', NODE_PATH: '', MUSE_DESKTOP_TEST: '1', MUSE_FIXTURE_URL: service, MUSE_DESKTOP_DATA: profile, MUSE_TRANSPORT: 'browser' };
  delete env.PORT;
  let desktop;
  try {
    desktop = await _electron.launch({ executablePath, args: process.env.MUSE_ELECTRON_TEST_NO_SANDBOX === '1' ? ['--no-sandbox', '--disable-gpu'] : [], env, timeout: 30000 });
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
    await login.getByRole('button', { name: 'Fixture login', exact: true }).click();
    await shell.getByRole('button', { name: '← Về Studio', exact: true }).click();
    await waitFor(async () => (await studio.locator('.connection-pill').innerText()).includes('Đã xác minh'));
    assert.equal(fixture.state.submitted.length, 0);
    await studio.getByRole('button', { name: 'Tạo ảnh hàng loạt', exact: true }).click();
    await studio.getByRole('button', { name: 'TẠO 10 ẢNH', exact: true }).click();
    await waitFor(async () => {
      const errors = await studio.locator('.scene-error pre').allTextContents();
      if (errors.length) throw new Error('Portable batch failed: ' + errors.join('\n'));
      return await studio.locator('.generated-image').count() === 10;
    }, 60000);
    assert.equal(fixture.state.submitted.length, 10);
    assert.equal(fixture.state.peak, 1);
    assert.equal(await studio.locator('.scene-error').count(), 0);
    assert.equal(fixture.state.submitted[0].initialMode, 'functional');
    assert.equal(fixture.state.submitted[0].authenticated, true);
    assert.match(fixture.state.submitted[0].prompt, /studio-request-/);
    const downloads = path.join(profile, 'downloads');
    await mkdir(downloads);
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
    await waitFor(async () => await desktop.evaluate(() => globalThis.fixtureDownloads.length) === 2);
    const saved = await desktop.evaluate(() => globalThis.fixtureDownloads);
    assert.ok(saved.every(file => file.state === 'completed'));
    assert.ok(saved[0].filename.endsWith('.png'));
    assert.ok(saved[1].filename.endsWith('.zip'));
    assert.equal(saved[0].filename, `image-001000-scene-01-${'b'.repeat(32)}.png`);
    assert.equal(saved[1].filename, `Muse-Images-10-001001-001010-${'b'.repeat(32)}.zip`);
    const hashes = new Set();
    const files = await readdir(downloads);
    assert.equal(files.length, 2, 'One click on Tải tất cả must start exactly one download');
    const archive = readZip(path.join(downloads, saved[1].filename));
    assert.deepEqual(archive.map(file => file.name), Array.from({ length: 10 }, (_, index) => `image-${String(index+1001).padStart(6,'0')}-scene-${String(index+1).padStart(2,'0')}-${'b'.repeat(32)}.png`));
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
    await desktop.firstWindow();
    await waitFor(() => { studio = desktop.context().pages().find(page => page.url() === studioURL); return studio; });
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
    assert.equal((await readdir(downloads)).length,3,'Reopening must continue the counter without overwriting any file');
    assert.equal(fixture.state.submitted.length,10);
  } finally {
    await desktop?.close();
    fixture.server.closeAllConnections();
    await new Promise(resolve => fixture.server.close(resolve));
    await rm(profile, { recursive: true, force: true });
  }
});
