import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createMuseFixture } from './fixtures/muse.mjs';
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
const { server: fixture, state, releaseAll } = createMuseFixture({ image, clip });

test('owned browser bridge against local Muse-shaped pages (not live Muse)', async t => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'muse-bridge-test-'));
  await new Promise(resolve => fixture.listen(0, '127.0.0.1', resolve));
  const driver = new MuseBrowser({ profileRoot: root, serviceURL: `http://127.0.0.1:${fixture.address().port}/`, launchOptions: { executablePath, headless: true }, pollMs: 30, quietMs: 80, timeoutMs: 15000 });
  const data = { accountId: 1, modelDisplayName: 'Omni 1.1 Flash', durationSeconds: 4, aspectRatio: '16:9', resolution: '360p', prompt: 'A forest at sunrise' };
  try {
    await t.test('does not infer authentication from the existence of a browser profile', async () => {
      const accounts = await driver.connect(1);
      assert.equal(accounts[0].authenticated, false);
      assert.equal(accounts[0].state, 'login_open');
      await assert.rejects(driver.generateVideo(data, new AbortController().signal), /MUSE_LOGIN_REQUIRED/);
      assert.equal(state.submitted.length, 0);
      await driver.active.page.getByText('Fixture login', { exact: true }).click();
      await driver.refreshActive();
      assert.equal(driver.snapshot()[0].authenticated, true);
    });
    await t.test('reconciles authenticated sessions with a stale signed-out page without sending a chat', async () => {
      const count = state.submitted.length;
      await driver.active.page.locator('[data-hatch-composer-root]').evaluate(root => root.style.display = 'none');
      await driver.refreshActive();
      assert.equal(driver.snapshot()[0].sessionAuthenticated, true);
      assert.equal(driver.snapshot()[0].authenticated, false);
      assert.equal(driver.snapshot()[0].state, 'composer_loading');
      await driver.connect(1, { show: false });
      assert.equal(driver.snapshot()[0].authenticated, true);
      assert.equal(state.submitted.length, count);
    });
    await t.test('keeps drafts when a session check finds a hidden composer', async () => {
      const page = driver.active.page;
      await page.locator('textarea').fill('Keep this unsent fixture draft');
      await page.locator('[data-hatch-composer-root]').evaluate(root => root.style.display = 'none');
      await driver.connect(1, { show: false });
      assert.equal(await page.locator('textarea').inputValue(), 'Keep this unsent fixture draft');
      assert.equal(driver.snapshot()[0].state, 'composer_loading');
      await page.locator('[data-hatch-composer-root]').evaluate(root => root.style.display = 'block');
      await page.locator('textarea').fill('');
      await driver.refreshActive();
    });
    await t.test('reports a failed auth probe distinctly and never trusts a composer alone', async () => {
      state.authStatus = 503;
      const count = state.submitted.length;
      try {
        await driver.refreshActive();
        assert.equal(driver.snapshot()[0].state, 'check_failed');
        assert.equal(driver.snapshot()[0].authenticated, false);
        assert.match(driver.snapshot()[0].connectionMessage, /HTTP 503/);
        await assert.rejects(driver.generateVideo(data, new AbortController().signal), /MUSE_SESSION_CHECK_FAILED/);
        assert.equal(state.submitted.length, count);
      } finally { state.authStatus = 200; await driver.refreshActive(); }
    });
    await t.test('submits the reference and returns the new playable video with observed metadata', async () => {
      state.behavior = 'video';
      const result = await driver.generateVideo({ ...data, referenceImage: { base64: png, mimeType: 'image/png' } }, new AbortController().signal);
      assert.equal(result.base64, clip.toString('base64'));
      assert.equal(result.mimeType, 'video/mp4');
      assert.equal(result.metadata.width, 640); assert.equal(result.metadata.height, 360);
      assert.ok(Math.abs(result.metadata.duration - 4) < 0.2);
      assert.equal(state.submitted.at(-1).attached, 1);
      assert.match(state.submitted.at(-1).prompt, /A forest at sunrise/);
      assert.match(state.submitted.at(-1).prompt, /Requested model: Omni 1.1 Flash/);
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
      state.behavior = 'image';
      const referenceImage = { base64: png, mimeType: 'image/png' };
      const locked = await driver.generateImage({ accountId: 1, prompt: 'Portrait in a forest', aspectRatio: '16:9', resolution: '4k', characterLock: true, referenceImage }, new AbortController().signal);
      assert.equal(locked.mimeType, 'image/png'); assert.equal(locked.base64, image.toString('base64'));
      assert.equal(locked.metadata.width, 640); assert.equal(locked.metadata.height, 360);
      assert.equal(state.submitted.at(-1).attached, 1); assert.match(state.submitted.at(-1).prompt, /3840x2160/);
      await driver.generateImage({ accountId: 1, prompt: 'A different person at sea', aspectRatio: '9:16', resolution: '2k', characterLock: false, referenceImage }, new AbortController().signal);
      assert.equal(state.submitted.at(-1).attached, 0); assert.match(state.submitted.at(-1).prompt, /A different person at sea/);
      assert.match(state.submitted.at(-1).prompt, /Do not reuse characters/);
      state.behavior = 'video';
      await driver.generateVideo({ ...data, sourceMode: 'image', characterLock: false, resolution: '1080p', referenceImage: { base64: locked.base64, mimeType: locked.mimeType } }, new AbortController().signal);
      assert.equal(state.submitted.at(-1).attached, 1); assert.match(state.submitted.at(-1).prompt, /starting frame/);
      assert.match(state.submitted.at(-1).prompt, /1080p/);
    });
    await t.test('reads only the new text turn and preserves an unrelated unsent draft', async () => {
      state.behavior = 'text';
      const result = await driver.generateText({ accountId: 1, prompt: 'Enhance the scene' }, new AbortController().signal);
      assert.equal(result.text, 'A new cinematic prompt, not old history.');
      await driver.active.page.locator('textarea').fill('My private unsent draft');
      const count = state.submitted.length;
      await driver.generateText({ accountId: 1, prompt: 'Separate worker must preserve the login draft' }, new AbortController().signal);
      await assert.rejects(driver.connect(2), /ACCOUNT_INVALID/);
      assert.equal(driver.active.id, 1);
      assert.equal(state.submitted.length, count + 1);
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
      state.behavior = 'text'; driver.timeoutMs = 500;
      await assert.rejects(driver.generateVideo(data, new AbortController().signal), /MUSE_TIMEOUT/);
      driver.timeoutMs = 15000;
    });
    await t.test('preserves provider errors and sends Stop when locally cancelled', async () => {
      state.behavior = 'error';
      await assert.rejects(driver.generateVideo(data, new AbortController().signal), /429 quota exhausted/);
      state.behavior = 'slow';
      const control = new AbortController();
      const task = driver.generateVideo(data, control.signal);
      const count = state.submitted.length;
      await waitFor(() => state.submitted.length > count);
      control.abort();
      await assert.rejects(task, error => error.name === 'AbortError');
      assert.equal(state.stops, 1);
    });
    await t.test('ignores the hidden prehydration textarea before the visible rich editor reported by the user', async () => {
      state.prehydrationInput = true; state.richComposer = true; state.behavior = 'image';
      try {
        const probe = await driver.active.context.newPage();
        try {
          await probe.goto(driver.serviceURL);
          assert.equal(await probe.locator('[data-hatch-composer-root] textarea, [data-hatch-composer-root] [contenteditable="true"]').first().isVisible(), false);
          assert.equal(await probe.locator('[data-lexical-editor="true"]').isVisible(), true);
        } finally { await probe.close(); }
        const count = state.submitted.length;
        const result = await driver.generateImage({ accountId: 1, prompt: 'Regression: use the visible composer', aspectRatio: '16:9', resolution: '2k', characterLock: false }, new AbortController().signal);
        assert.equal(result.base64, image.toString('base64'));
        assert.equal(state.submitted.length, count + 1);
        assert.equal(state.submitted.at(-1).prehydrationValue, '');
      } finally { state.prehydrationInput = false; state.richComposer = false; }
    });
    await t.test('waits for the hydrated editor and never submits to a visible prehydration placeholder', async () => {
      state.prehydrationInput = true; state.richComposer = true; state.hydrationDelayMs = 600; state.behavior = 'image';
      const originalTimeout = driver.composerTimeoutMs;
      const count = state.submitted.length;
      const request = { accountId: 1, prompt: 'Wait for Muse hydration', aspectRatio: '16:9', resolution: '2k', characterLock: false };
      try {
        driver.composerTimeoutMs = 100;
        await assert.rejects(driver.generateImage(request, new AbortController().signal), /MUSE_COMPOSER_NOT_READY/);
        assert.equal(state.submitted.length, count);
        driver.composerTimeoutMs = 3000;
        const result = await driver.generateImage(request, new AbortController().signal);
        assert.equal(result.base64, image.toString('base64'));
        assert.equal(state.submitted.length, count + 1);
        assert.equal(state.submitted.at(-1).prehydrationValue, '');
      } finally { driver.composerTimeoutMs = originalTimeout; state.prehydrationInput = false; state.richComposer = false; state.hydrationDelayMs = 0; }
    });
    await t.test('runs ten isolated image conversations simultaneously with one session and maps each output correctly', async () => {
      state.behavior = 'image'; state.hold = true; state.uniqueImages = true; state.peak = 0;
      const first = state.submitted.length;
      const tasks = Array.from({ length: 10 }, (_, i) => driver.generateImage({ accountId: 1, prompt: `Concurrent scene ${i + 1}`, aspectRatio: '16:9', resolution: '2k', characterLock: false }, new AbortController().signal));
      try {
        await waitFor(() => state.pending.size === 10);
        assert.equal(state.peak, 10);
        assert.equal(driver.workers.size, 10);
        await assert.rejects(driver.generateVideo(data, new AbortController().signal), /MUSE_CONCURRENCY_LIMIT/);
      } finally { releaseAll(); state.hold = false; }
      const results = await Promise.all(tasks);
      assert.equal(new Set(results.map(result => result.base64)).size, 10);
      for (let i = 0; i < 10; i++) {
        const request = state.submitted.slice(first).find(request => request.prompt.includes(`Scene:\nConcurrent scene ${i + 1}\n`));
        assert.ok(request?.authenticated);
        assert.equal(results[i].base64, state.outputs.get(request.id));
      }
      assert.equal(driver.workers.size, 0);
      assert.equal(driver.snapshot().length, 1);
      state.uniqueImages = false;
    });
    await t.test('refuses a reused conversation unless a fresh chat can be opened', async () => {
      state.oldConversation = true; state.newChat = false; state.behavior = 'video';
      const count = state.submitted.length;
      await assert.rejects(driver.generateVideo(data, new AbortController().signal), /MUSE_NEW_CHAT_UNAVAILABLE/);
      assert.equal(state.submitted.length, count);
      state.newChat = true;
      await driver.generateVideo(data, new AbortController().signal);
      assert.equal(state.submitted.length, count + 1);
      state.oldConversation = false;
    });
    await t.test('checks authentication again before every send, including an expired saved session', async () => {
      await driver.active.page.evaluate(() => { document.cookie = 'fixture_session=; Max-Age=0'; });
      const count = state.submitted.length;
      await assert.rejects(driver.generateVideo(data, new AbortController().signal), /MUSE_LOGIN_REQUIRED/);
      assert.equal(state.submitted.length, count);
      assert.equal(driver.snapshot()[0].authenticated, false);
    });
  } finally { await driver.close(); fixture.closeAllConnections(); await new Promise(resolve => fixture.close(resolve)); await rm(root, { recursive: true, force: true }); }
});

async function waitFor(predicate) { const deadline = Date.now() + 20000; while (!predicate()) { if (Date.now() > deadline) throw new Error('Fixture condition timed out'); await new Promise(resolve => setTimeout(resolve, 25)); } }
