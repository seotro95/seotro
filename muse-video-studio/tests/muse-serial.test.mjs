import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { randomUUID } from 'node:crypto';
import { createMuseFixture } from './fixtures/muse.mjs';
import { MuseBrowser } from '../muse-browser.mjs';

if (!process.env.CHROMIUM_PATH) throw new Error('Set CHROMIUM_PATH.');
const image = await readFile(new URL('../public/demo-image.png', import.meta.url));
const clip = await readFile(new URL('../public/demo.mp4', import.meta.url));
async function waitFor(predicate) {
  const deadline = Date.now() + 30000;
  while (!await predicate()) {
    if (Date.now() > deadline) throw new Error('Serial fixture condition timed out.');
    await new Promise(resolve => setTimeout(resolve, 25));
  }
}
const pngSignature = Buffer.from([137,80,78,71,13,10,26,10]);
function assertPNG(result) {
  assert.equal(result.mimeType, 'image/png');
  const bytes = Buffer.from(result.base64, 'base64');
  assert.ok(bytes.subarray(0,8).equals(pngSignature));
  assert.equal(bytes.readUInt32BE(16), 640);
  assert.equal(bytes.readUInt32BE(20), 360);
}

test('one persistent Muse conversation processes a full batch without New chat and rejects ambiguous or duplicate results', { timeout: 120000 }, async t => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'muse-serial-test-'));
  const fixture = createMuseFixture({ image, clip });
  Object.assign(fixture.state, { behavior: 'image', uniqueImages: true, oldConversation: true, newChat: false, sharedHistory: true });
  await new Promise(resolve => fixture.server.listen(0, '127.0.0.1', resolve));
  const driver = new MuseBrowser({ profileRoot: root, serviceURL: `http://127.0.0.1:${fixture.server.address().port}/`, launchOptions: { executablePath: process.env.CHROMIUM_PATH, headless: true }, pollMs: 30, quietMs: 50, timeoutMs: 15000 });
  const render = (sceneId, batchId = randomUUID(), signal = new AbortController().signal) => driver.generateImage({ accountId: 1, prompt: `Different scene ${sceneId}`, aspectRatio: '16:9', resolution: '2k', characterLock: false, batchId, sceneId }, signal);
  try {
    await driver.connect();
    await driver.active.page.getByRole('button', { name: 'Fixture login', exact: true }).click();
    await driver.refreshActive();
    await t.test('ten submissions are queued on one account, reuse history and return ten different images', async () => {
      assert.equal(driver.maxConcurrency, 1);
      fixture.state.hold = true;
      const batch = randomUUID();
      const tasks = Array.from({ length: 10 }, (_, index) => render(index + 1, batch));
      const results = Promise.all(tasks);
      for (let index = 0; index < 10; index++) {
        await waitFor(() => fixture.state.submitted.length === index + 1 && fixture.state.pending.size === 1);
        assert.equal(driver.executing, 1);
        fixture.releaseAll();
      }
      const outputs = await results;
      assert.equal(fixture.state.peak, 1);
      assert.equal(new Set(outputs.map(output => output.fingerprint)).size, 10);
      for (const [index, output] of outputs.entries()) {
        assertPNG(output);
        assert.equal(output.base64, fixture.state.outputs.get(index + 1));
        assert.match(fixture.state.submitted[index].prompt, new RegExp(`Different scene ${index + 1}(?:\\n|$)`));
        assert.equal(fixture.state.submitted[index].authenticated, true);
      }
      assert.equal(driver.reserved, 0);
      fixture.state.hold = false;
    });
    await t.test('cancelled queued work never submits a prompt', async () => {
      fixture.state.hold = true;
      const count = fixture.state.submitted.length;
      const first = render(1);
      await waitFor(() => fixture.state.pending.size === 1);
      const cancel = new AbortController();
      const second = render(2, randomUUID(), cancel.signal);
      const rejected = assert.rejects(second, error => error.name === 'AbortError');
      cancel.abort(); await rejected;
      assert.equal(fixture.state.submitted.length, count + 1);
      fixture.releaseAll(); await first;
      assert.equal(driver.reserved, 0);
      fixture.state.hold = false;
    });
    await t.test('a duplicate image is flagged instead of completing a different scene', async () => {
      fixture.state.uniqueImages = false;
      const batch = randomUUID();
      await render(1, batch);
      const count = fixture.state.submitted.length;
      await assert.rejects(render(2, batch), /MUSE_DUPLICATE_MEDIA/);
      assert.equal(fixture.state.submitted.length, count + 1);
      await assert.rejects(render(3, randomUUID()), /MUSE_DUPLICATE_MEDIA/);
      assert.equal(fixture.state.submitted.length, count + 2);
    });
    await t.test('WebP bytes with an incorrect MIME are returned as real PNG with native dimensions', async () => {
      fixture.state.uniqueImages = true; fixture.state.imageEncoding = 'image/webp';
      const converted = await render(1);
      assertPNG(converted);
      const rawWebP = Buffer.from(fixture.state.outputs.get(fixture.state.submitted.length), 'base64');
      assert.equal(rawWebP.toString('ascii', 8, 12), 'WEBP');
      fixture.state.uniqueImages = false; fixture.state.assetImageBytes = rawWebP; fixture.state.assetImageMime = 'application/octet-stream';
      const corrected = await render(1);
      assertPNG(corrected);
      assert.equal(corrected.fingerprint, converted.fingerprint);
      fixture.state.assetImageBytes = null; fixture.state.assetImageMime = null; fixture.state.imageEncoding = null;
    });
    await t.test('an image after a different user turn is never assigned to this request', async () => {
      fixture.state.foreignTurn = true;
      const count = fixture.state.submitted.length;
      await assert.rejects(render(1), /MUSE_SHARED_CONVERSATION/);
      assert.equal(fixture.state.submitted.length, count + 1);
    });
  } finally {
    fixture.releaseAll(); await driver.close(); fixture.server.closeAllConnections();
    await new Promise(resolve => fixture.server.close(resolve));
    await rm(root, { recursive: true, force: true });
  }
});
