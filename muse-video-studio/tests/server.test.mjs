import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { spawn } from 'node:child_process';
import { readFile } from 'node:fs/promises';

const image = (await readFile(new URL('../public/demo-image.png', import.meta.url))).toString('base64');
const clip = (await readFile(new URL('../public/demo.mp4', import.meta.url))).toString('base64');
const calls = [];
let adapterMode = 'ok';
const releases = [];
const adapter = http.createServer(async (req, res) => {
  let raw = ''; for await (const chunk of req) raw += chunk;
  calls.push({ path: req.url, auth: req.headers.authorization, body: JSON.parse(raw) });
  if (adapterMode === 'wait') await new Promise(r => { releases.push(r); });
  res.setHeader('Content-Type', 'application/json');
  if (adapterMode === 'error') { res.writeHead(429); return res.end(JSON.stringify({ error: '429 quota exhausted; Bearer test-bridge-secret' })); }
  res.end(JSON.stringify(req.url === '/text' ? { text: 'A cinematic scene in English.' } : req.url === '/image' ? { base64: image, mimeType: 'image/png' } : { base64: clip, mimeType: 'video/mp4' }));
});
const payload = { accountId: 1, prompt: 'A cinematic forest scene', model: 'Omni 1.1 Flash', aspectRatio: '9:16', duration: 6, resolution: '720p', image: { imageBytes: 'aGVsbG8=', mimeType: 'image/png' } };

test('server adapter integration (local test server, not real Muse.ai)', async t => {
  await new Promise(resolve => adapter.listen(0, '127.0.0.1', resolve));
  const child = spawn(process.execPath, ['server.mjs'], { cwd: new URL('../', import.meta.url),
    env: { ...process.env, PORT: '0', MUSE_TRANSPORT: 'adapter', MUSE_ADAPTER_URL: `http://127.0.0.1:${adapter.address().port}`, MUSE_ADAPTER_TOKEN: 'test-bridge-secret' }, stdio: ['ignore', 'pipe', 'pipe'] });
  try {
    const base = await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('Server startup timed out')), 10000);
      child.once('error', e => { clearTimeout(timeout); reject(e); });
      child.once('exit', code => { clearTimeout(timeout); reject(new Error(`Server exited ${code}`)); });
      child.stdout.on('data', chunk => { const match = String(chunk).match(/http:\/\/127\.0\.0\.1:\d+/); if (match) { clearTimeout(timeout); resolve(match[0]); } });
    });
    const post = (endpoint, data, headers = {}) => fetch(base + endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json', ...headers }, body: JSON.stringify(data) });
    await t.test('static app and honest status, no credential values', async () => {
      assert.equal((await fetch(base)).status, 200);
      const status = await (await fetch(base + '/api/status')).json();
      assert.deepEqual(status, { museConfigured: true, transport: 'adapter', accounts: [], busy: false, activeRequests: 0, maxConcurrency: 40, embeddedLogin: false, credit: null, gpu: null });
      assert.equal(JSON.stringify(status).includes('test-bridge-secret'), false);
      assert.equal((await fetch(base + '/.env')).status, 404);
    });
    await t.test('passes the single account, image and model to authenticated adapter', async () => {
      const result = await post('/api/video', payload);
      assert.equal(result.status, 200);
      assert.equal((await result.json()).base64, clip);
      const call = calls.at(-1);
      assert.equal(call.path, '/video'); assert.equal(call.auth, 'Bearer test-bridge-secret');
      assert.deepEqual(call.body, { accountId: 1, prompt: payload.prompt, modelDisplayName: payload.model, aspectRatio: '9:16', durationSeconds: 6, resolution: '720p', characterLock: true, sourceMode: 'text', referenceImage: { base64: 'aGVsbG8=', mimeType: 'image/png' } });
    });
    await t.test('rejects invalid account/model constraints and cross-origin writes before adapter', async () => {
      const count = calls.length;
      assert.equal((await post('/api/video', { ...payload, accountId: 11 })).status, 400);
      assert.equal((await post('/api/video', { ...payload, accountId: 2 })).status, 400);
      assert.equal((await post('/api/accounts/2/connect', {})).status, 400);
      assert.equal((await post('/api/video', { ...payload, model: 'Veo 3.1 - Fast', duration: 4 })).status, 400);
      assert.equal((await post('/api/video', payload, { Origin: 'https://other-site.example' })).status, 403);
      assert.equal(calls.length, count);
    });
    await t.test('accepts requested 4K video and 2K/4K images; independent images omit references', async () => {
      const video = await post('/api/video', { ...payload, resolution: '4k', model: 'Veo 3.1 - Fast', duration: 8 });
      assert.equal(video.status, 200); assert.equal(calls.at(-1).body.resolution, '4k');
      const result = await post('/api/image', { accountId: 1, prompt: 'A new scene', aspectRatio: '9:16', resolution: '4k', characterLock: false, image: payload.image });
      assert.equal(result.status, 200); assert.equal((await result.json()).mimeType, 'image/png');
      assert.equal(calls.at(-1).path, '/image'); assert.equal(calls.at(-1).body.referenceImage, undefined);
      assert.equal(calls.at(-1).body.characterLock, false);
      const count = calls.length;
      assert.equal((await post('/api/video', { ...payload, image: undefined, sourceMode: 'image' })).status, 400);
      assert.equal(calls.length, count);
      const fromImage = await post('/api/video', { ...payload, sourceMode: 'image', characterLock: false });
      assert.equal(fromImage.status, 200); assert.equal(calls.at(-1).body.referenceImage.base64, payload.image.imageBytes);
    });
    await t.test('routes enhancement to text endpoint', async () => {
      const result = await post('/api/text', { accountId: 1, prompt: 'Enhance this scene' });
      assert.equal((await result.json()).text, 'A cinematic scene in English.');
      assert.equal(calls.at(-1).path, '/text'); assert.equal(calls.at(-1).body.accountId, 1);
    });
    await t.test('preserves credit error code and redacts adapter secret', async () => {
      adapterMode = 'error';
      const result = await post('/api/video', payload);
      assert.equal(result.status, 429);
      const { error } = await result.json();
      assert.match(error, /429 quota exhausted/); assert.equal(error.includes('test-bridge-secret'), false);
      adapterMode = 'ok';
    });
    await t.test('admits forty parallel requests and keeps the remaining slots busy when one finishes', async () => {
      adapterMode = 'wait';
      const tasks = Array.from({ length: 40 }, (_, i) => post('/api/video', { ...payload, prompt: `Parallel scene ${i + 1}` }));
      await waitFor(() => releases.length === 40);
      let status = await (await fetch(base + '/api/status')).json();
      assert.equal(status.activeRequests, 40); assert.equal(status.busy, true);
      assert.equal((await post('/api/video', payload)).status, 429);
      assert.equal((await post('/api/account/close', {})).status, 409);
      releases.shift()();
      assert.equal((await tasks[0]).status, 200);
      status = await (await fetch(base + '/api/status')).json();
      assert.equal(status.activeRequests, 39); assert.equal(status.busy, true);
      const replacement = post('/api/video', payload);
      await waitFor(() => releases.length === 40);
      assert.equal((await post('/api/video', payload)).status, 429);
      for (const release of releases.splice(0)) release();
      adapterMode = 'ok';
      for (const response of await Promise.all([...tasks, replacement])) assert.equal(response.status, 200);
      status = await (await fetch(base + '/api/status')).json();
      assert.equal(status.activeRequests, 0); assert.equal(status.busy, false);
    });
  } finally { child.kill('SIGTERM'); adapter.closeAllConnections(); await new Promise(resolve => adapter.close(resolve)); }
});

async function waitFor(predicate) { const deadline = Date.now() + 5000; while (!predicate()) { if (Date.now() > deadline) throw new Error('Adapter barrier timed out'); await new Promise(resolve => setTimeout(resolve, 10)); } }
