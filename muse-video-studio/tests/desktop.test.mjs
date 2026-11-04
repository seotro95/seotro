import { test } from 'node:test';
import assert from 'node:assert/strict';
import { _electron } from 'playwright-core';
import { createRequire } from 'node:module';
import { mkdtemp, readFile, rm, mkdir } from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createMuseFixture } from './fixtures/muse.mjs';

const require = createRequire(import.meta.url);
const directory = path.dirname(fileURLToPath(import.meta.url));
const root = path.dirname(directory);
const image = await readFile(path.join(root, 'public/demo-image.png'));
const clip = await readFile(path.join(root, 'public/demo.mp4'));

async function waitFor(predicate, label) {
  const deadline = Date.now() + 30000;
  while (!await predicate()) {
    if (Date.now() > deadline) throw new Error(`Timed out: ${label}`);
    await new Promise(resolve => setTimeout(resolve, 30));
  }
}

test('desktop embeds login and runs ten real Electron workers with one fixture session (not live Muse)', { timeout: 120000 }, async t => {
  const profile = await mkdtemp(path.join(os.tmpdir(), 'muse-desktop-test-'));
  const fixture = createMuseFixture({ image, clip });
  await new Promise(resolve => fixture.server.listen(0, '127.0.0.1', resolve));
  const fixtureURL = `http://127.0.0.1:${fixture.server.address().port}/`;
  let desktop;
  try {
    desktop = await _electron.launch({ executablePath: require('electron'), args: [
      ...(process.env.MUSE_ELECTRON_TEST_NO_SANDBOX === '1' ? ['--no-sandbox', '--disable-gpu'] : []),
      path.join(root, 'desktop/main.mjs'),
    ], env: { ...process.env, MUSE_DESKTOP_TEST: '1', MUSE_FIXTURE_URL: fixtureURL, MUSE_DESKTOP_DATA: profile, MUSE_TRANSPORT: 'browser', PORT: '0' }, timeout: 30000 });
    await desktop.firstWindow();
    let shell;
    const shellURL = pathToFileURL(path.join(root, 'desktop/shell.html')).href;
    await waitFor(() => { shell = desktop.context().pages().find(page => page.url() === shellURL); return shell; }, 'desktop shell');
    let studio;
    await waitFor(() => { studio = desktop.context().pages().find(page => page.url().startsWith('http://127.0.0.1:') && !page.url().startsWith(fixtureURL)); return studio; }, 'Studio page');
    let login;
    await t.test('one app window contains the real login view, isolated from Node APIs', async () => {
      await studio.getByRole('button', { name: 'Đăng nhập Muse trong tool', exact: true }).click();
      await waitFor(() => { login = desktop.context().pages().find(page => page.url() === fixtureURL); return login; }, 'embedded Muse view');
      assert.equal(await login.evaluate(() => typeof window.require), 'undefined');
      assert.equal(await login.evaluate(() => typeof window.studioDesktop), 'undefined');
      assert.equal(await login.evaluate(() => typeof window.museTransport), 'undefined');
      assert.equal(await desktop.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows().length), 1);
      await login.getByRole('button', { name: 'Fixture login', exact: true }).click();
      await shell.getByRole('button', { name: '← Về Studio', exact: true }).click();
      await studio.getByRole('button', { name: 'Kiểm tra phiên', exact: true }).click();
      await waitFor(async () => (await studio.locator('.single-account-controls').innerText()).includes('Đã xác minh'), 'verified embedded login');
      const status = await studio.evaluate(async () => (await fetch('/api/status')).json());
      assert.equal(status.embeddedLogin, true);
      assert.equal(status.maxConcurrency, 10);
      assert.equal(status.accounts.length, 1);
      assert.equal(status.accounts[0].authenticated, true);
      await assert.rejects(studio.evaluate(() => window.museTransport.request(crypto.randomUUID(), 'https://example.com', {})), /Invalid Studio request/);
    });
    await t.test('ten image jobs overlap before any response, share login, and keep scene outputs separate', async () => {
      fixture.state.behavior = 'image'; fixture.state.hold = true; fixture.state.uniqueImages = true;
      for (let i = 1; i <= 10; i++) await studio.getByLabel(`Kịch bản cảnh ${i}`, { exact: true }).fill(`Desktop image ${i}`);
      await studio.getByRole('button', { name: 'Tạo ảnh hàng loạt', exact: true }).click();
      await studio.getByRole('button', { name: 'TẠO 10 ẢNH', exact: true }).click();
      await waitFor(() => fixture.state.pending.size === 10, 'ten concurrent embedded requests');
      assert.equal(fixture.state.peak, 10);
      assert.ok(fixture.state.submitted.every(request => request.authenticated));
      assert.equal(await studio.locator('.status-badge.running').count(), 10);
      assert.equal(await studio.locator('.generated-image').count(), 0);
      const activeStatus = await studio.evaluate(async () => (await fetch('/api/status')).json());
      assert.equal(activeStatus.activeRequests, 10);
      assert.equal(activeStatus.accounts.length, 1);
      fixture.releaseAll(); fixture.state.hold = false;
      await waitFor(async () => await studio.locator('.generated-image').count() === 10, 'ten image results');
      for (let i = 1; i <= 10; i++) {
        const request = fixture.state.submitted.find(request => request.prompt.includes(`Scene:\nDesktop image ${i}\n`));
        assert.ok(request);
        const actual = await studio.getByTestId(`scene-${i}`).locator('.generated-image').evaluate(async image => {
          const blob = await (await fetch(image.src)).blob();
          return new Promise(resolve => { const reader = new FileReader(); reader.onload = () => resolve(reader.result.split(',')[1]); reader.readAsDataURL(blob); });
        });
        assert.equal(actual, fixture.state.outputs.get(request.id));
      }
      await mkdir(path.join(root, 'test-results'), { recursive: true });
      await studio.screenshot({ path: path.join(root, 'test-results/desktop-app-studio.png') });
    });
    await t.test('ten image-to-video workers overlap on the same session and clean up afterwards', async () => {
      await waitFor(async () => await studio.getByRole('button', { name: 'Chuyển bộ ảnh đã tạo sang video', exact: true }).isEnabled(), 'finished image batch');
      await studio.getByRole('button', { name: 'Chuyển bộ ảnh đã tạo sang video', exact: true }).click();
      fixture.state.behavior = 'video'; fixture.state.hold = true; fixture.state.peak = 0;
      await studio.getByRole('button', { name: 'TẠO 10 VIDEO', exact: true }).click();
      await waitFor(() => fixture.state.pending.size === 10, 'ten concurrent video requests');
      assert.equal(fixture.state.peak, 10);
      assert.ok(fixture.state.submitted.slice(10).every(request => request.authenticated && request.attached === 1));
      fixture.releaseAll(); fixture.state.hold = false;
      await waitFor(async () => await studio.locator('.scene-card video').count() === 10, 'ten video results');
      assert.equal(await studio.locator('.generated-image').count(), 0);
      await waitFor(() => desktop.context().pages().length === 3, 'worker views closed, login and Studio retained');
      const status = await studio.evaluate(async () => (await fetch('/api/status')).json());
      assert.equal(status.activeRequests, 0);
      assert.equal(status.accounts.length, 1);
    });
    await t.test('Stop aborts all ten IPC requests and sends Stop to each active Muse conversation', async () => {
      fixture.state.behavior = 'slow'; fixture.state.hold = false;
      const count = fixture.state.submitted.length;
      for (let i = 1; i <= 10; i++) await studio.getByLabel(`Kịch bản cảnh ${i}`, { exact: true }).fill(`Cancel scene ${i}`);
      await studio.getByRole('button', { name: 'TẠO 10 VIDEO', exact: true }).click();
      await waitFor(() => fixture.state.submitted.length === count + 10, 'ten cancellable workers');
      await studio.getByRole('button', { name: 'Dừng tất cả luồng', exact: true }).click();
      await waitFor(async () => await studio.locator('.status-badge.cancelled').count() === 10, 'all ten client requests cancelled');
      await waitFor(() => fixture.state.stops === 10, 'Stop reached each Muse conversation');
      await waitFor(() => desktop.context().pages().length === 3, 'cancelled workers disposed');
      const status = await studio.evaluate(async () => (await fetch('/api/status')).json());
      assert.equal(status.activeRequests, 0);
    });
    await t.test('closing and reopening the app restores the same embedded session without another login', async () => {
      await desktop.close(); desktop = null;
      desktop = await _electron.launch({ executablePath: require('electron'), args: [
        ...(process.env.MUSE_ELECTRON_TEST_NO_SANDBOX === '1' ? ['--no-sandbox', '--disable-gpu'] : []), path.join(root, 'desktop/main.mjs'),
      ], env: { ...process.env, MUSE_DESKTOP_TEST: '1', MUSE_FIXTURE_URL: fixtureURL, MUSE_DESKTOP_DATA: profile, MUSE_TRANSPORT: 'browser', PORT: '0' }, timeout: 30000 });
      await desktop.firstWindow();
      await waitFor(() => { studio = desktop.context().pages().find(page => page.url().startsWith('http://127.0.0.1:') && !page.url().startsWith(fixtureURL)); return studio; }, 'reopened Studio');
      await studio.getByRole('button', { name: 'Đăng nhập Muse trong tool', exact: true }).click();
      await waitFor(async () => (await studio.locator('.single-account-controls').innerText()).includes('Đã xác minh'), 'restored saved Muse session');
      const status = await studio.evaluate(async () => (await fetch('/api/status')).json());
      assert.equal(status.accounts.length, 1);
      assert.equal(status.accounts[0].authenticated, true);
    });
  } finally {
    fixture.releaseAll();
    await desktop?.close();
    fixture.server.closeAllConnections();
    await new Promise(resolve => fixture.server.close(resolve));
    await rm(profile, { recursive: true, force: true });
  }
});
