import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { randomUUID } from 'node:crypto';
import { createMuseFixture } from './fixtures/muse.mjs';
import { MuseBrowser } from '../muse-browser.mjs';
import { startStudioServer } from '../server.mjs';

if (!process.env.CHROMIUM_PATH) throw new Error('Set CHROMIUM_PATH.');
const image = await readFile(new URL('../public/demo-image.png', import.meta.url));
const clip = await readFile(new URL('../public/demo.mp4', import.meta.url));
async function waitFor(predicate) {
  const deadline = Date.now() + 30000;
  while (!await predicate()) {
    if (Date.now() > deadline) throw new Error('Parallel fixture timed out.');
    await new Promise(resolve => setTimeout(resolve, 25));
  }
}

test('parallel mode verifies service-created chat routes without rendering, and cancellation isolates one scene', { timeout: 120000 }, async t => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'muse-parallel-test-'));
  const fixture = createMuseFixture({ image, clip });
  Object.assign(fixture.state, { behavior: 'image', uniqueImages: true, newChat: false, sharedHistory: true });
  await new Promise(resolve => fixture.server.listen(0, '127.0.0.1', resolve));
  const driver = new MuseBrowser({ profileRoot: root, serviceURL: `http://127.0.0.1:${fixture.server.address().port}/`, launchOptions: { executablePath: process.env.CHROMIUM_PATH, headless: true }, pollMs: 30, quietMs: 50, timeoutMs: 15000 });
  const runtime = await startStudioServer({ museDriver: driver, port: 0 });
  const change = count => fetch(runtime.url + '/api/account/concurrency', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ concurrency: count }) });
  try {
    await driver.connect();
    await driver.active.page.getByRole('button', { name: 'Fixture login', exact: true }).click();
    await driver.refreshActive();
    await t.test('invalid counts and missing New chat never render or enable parallelism', async () => {
      assert.equal((await change(0)).status, 400);
      assert.equal((await change('10')).status, 400);
      const result = await change(10);
      assert.equal(result.status, 409);
      assert.match((await result.json()).error, /MUSE_PARALLEL_UNVERIFIED/);
      assert.equal(driver.maxConcurrency, 1);
      assert.equal(fixture.state.submitted.length, 0);
    });
    await t.test('a New chat button that only clears the shared root page is insufficient', async () => {
      fixture.state.newChat = true;
      const result = await change(2);
      assert.equal(result.status, 409);
      assert.match((await result.json()).error, /MUSE_PARALLEL_UNVERIFIED/);
      assert.equal(driver.maxConcurrency, 1);
      assert.equal(fixture.state.submitted.length, 0);
    });
    await t.test('ten persistent chat URLs permit ten requests, one Stop leaves nine running', async () => {
      fixture.state.chatRoutes = true;
      const result = await change(10);
      assert.equal(result.status, 200);
      assert.equal((await result.json()).executionConcurrency, 10);
      assert.equal(fixture.state.submitted.length, 0, 'capability checking must not generate paid content');
      assert.equal(new Set(driver.parallelRoutes.map(route => route.url)).size, 10);
      fixture.state.hold = true;
      const controls = Array.from({ length: 10 }, () => new AbortController());
      const batchId = randomUUID();
      const tasks = controls.map((control, index) => driver.generateImage({ accountId: 1, prompt: `Parallel scene ${index + 1}`, aspectRatio: '16:9', resolution: '2k', characterLock: false, batchId, sceneId: index + 1 }, control.signal));
      const settled = Promise.allSettled(tasks);
      await waitFor(() => fixture.state.submitted.length === 10);
      await waitFor(() => driver.progress().filter(stage => stage.active && stage.submitted).length === 10);
      assert.ok(driver.progress().every(stage => !('prompt' in stage) && !('url' in stage)));
      assert.equal(fixture.state.peak, 10);
      assert.equal(new Set(fixture.state.submitted.map(request => request.path)).size, 10);
      assert.equal((await change(1)).status, 409);
      controls[3].abort();
      await waitFor(() => fixture.state.stops === 1);
      fixture.releaseAll();
      const outputs = await settled;
      assert.equal(outputs.filter(output => output.status === 'fulfilled').length, 9);
      assert.equal(outputs[3].status, 'rejected');
      assert.equal(outputs[3].reason.name, 'AbortError');
      assert.equal(new Set(outputs.filter(output => output.status === 'fulfilled').map(output => output.value.fingerprint)).size, 9);
      assert.equal(fixture.state.stops, 1);
      assert.equal(driver.reserved, 0);
      fixture.state.hold = false;
    });
    await t.test('redirected chat routes downgrade before sending another prompt', async () => {
      fixture.state.redirectChats = true;
      const count = fixture.state.submitted.length;
      await assert.rejects(driver.generateImage({ accountId: 1, prompt: 'Must not submit', aspectRatio: '16:9', resolution: '2k' }, new AbortController().signal), /MUSE_PARALLEL_UNVERIFIED/);
      assert.equal(driver.maxConcurrency, 1);
      assert.equal(fixture.state.submitted.length, count);
      assert.equal((await change(1)).status, 200);
    });
  } finally {
    fixture.releaseAll(); await runtime.close(); fixture.server.closeAllConnections();
    await new Promise(resolve => fixture.server.close(resolve));
    await rm(root, { recursive: true, force: true });
  }
});
