import { test } from 'node:test';
import assert from 'node:assert/strict';
import { _electron } from 'playwright-core';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { createMuseFixture } from './fixtures/muse.mjs';

const executablePath = process.env.MUSE_PORTABLE_EXECUTABLE;
if (!executablePath) throw new Error('Set MUSE_PORTABLE_EXECUTABLE to a prepared portable Linux executable.');
const image = await readFile(new URL('../public/demo-image.png', import.meta.url));
const clip = await readFile(new URL('../public/demo.mp4', import.meta.url));
const version = JSON.parse(await readFile(new URL('../package.json', import.meta.url), 'utf8')).version;
async function waitFor(predicate) {
  const deadline = Date.now() + 30000;
  while (!await predicate()) {
    if (Date.now() > deadline) throw new Error('Portable app did not reach the expected state.');
    await new Promise(resolve => setTimeout(resolve, 40));
  }
}

test('portable app launches with a fresh profile and no external Node/npm, then generates using the retained-label Message field', { timeout: 90000 }, async () => {
  const profile = await mkdtemp(path.join(os.tmpdir(), 'muse-portable-test-'));
  const fixture = createMuseFixture({ image, clip });
  Object.assign(fixture.state, { prehydrationInput: true, richComposer: true, initialMode: 'functional', behavior: 'image' });
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
    await studio.getByTestId('scene-1').getByRole('button', { name: 'Tạo cảnh này', exact: true }).click();
    await waitFor(async () => await studio.getByTestId('scene-1').locator('.generated-image').count() === 1);
    assert.equal(fixture.state.submitted.length, 1);
    assert.equal(fixture.state.submitted[0].initialMode, 'functional');
    assert.equal(fixture.state.submitted[0].authenticated, true);
    assert.match(fixture.state.submitted[0].prompt, /studio-request-/);
    const studioURL = studio.url();
    const savedPrompt = 'A script saved by the complete portable app';
    await studio.getByLabel('Kịch bản cảnh 2', { exact: true }).fill(savedPrompt);
    await desktop.close(); desktop = null;
    desktop = await _electron.launch({ executablePath, args: process.env.MUSE_ELECTRON_TEST_NO_SANDBOX === '1' ? ['--no-sandbox', '--disable-gpu'] : [], env, timeout: 30000 });
    await desktop.firstWindow();
    await waitFor(() => { studio = desktop.context().pages().find(page => page.url() === studioURL); return studio; });
    assert.equal(await studio.getByLabel('Kịch bản cảnh 2', { exact: true }).inputValue(), savedPrompt);
  } finally {
    await desktop?.close();
    fixture.server.closeAllConnections();
    await new Promise(resolve => fixture.server.close(resolve));
    await rm(profile, { recursive: true, force: true });
  }
});
