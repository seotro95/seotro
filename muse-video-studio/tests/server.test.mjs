import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { spawn } from 'node:child_process';
import { readFile } from 'node:fs/promises';

const clip = (await readFile(new URL('../public/demo.mp4', import.meta.url))).toString('base64');
const calls = [];
let adapterMode = 'ok';
let release;
const adapter = http.createServer(async (req, res) => {
  let raw = ''; for await (const chunk of req) raw += chunk;
  calls.push({ path: req.url, auth: req.headers.authorization, body: JSON.parse(raw) });
  if (adapterMode === 'wait') await new Promise(r => { release = r; });
  res.setHeader('Content-Type', 'application/json');
  if (adapterMode === 'error') { res.writeHead(429); return res.end(JSON.stringify({ error: '429 quota exhausted; Bearer test-bridge-secret' })); }
  res.end(JSON.stringify(req.url === '/text' ? { text: 'A cinematic scene in English.' } : { base64: clip, mimeType: 'video/mp4' }));
});
const payload = { accountId: 7, prompt: 'A cinematic forest scene', model: 'Omni 1.1 Flash', aspectRatio: '9:16', duration: 6, resolution: '720p', image: { imageBytes: 'aGVsbG8=', mimeType: 'image/png' } };

test('server adapter integration (local test server, not real Muse.ai)', async t => {
  await new Promise(resolve => adapter.listen(0, '127.0.0.1', resolve));
  const child = spawn(process.execPath, ['server.mjs'], { cwd: new URL('../', import.meta.url),
    env: { ...process.env, PORT: '0', MUSE_ADAPTER_URL: `http://127.0.0.1:${adapter.address().port}`, MUSE_ADAPTER_TOKEN: 'test-bridge-secret' }, stdio: ['ignore', 'pipe', 'pipe'] });
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
      assert.deepEqual(status, { museConfigured: true, busy: false, credit: null, gpu: null });
      assert.equal(JSON.stringify(status).includes('test-bridge-secret'), false);
      assert.equal((await fetch(base + '/.env')).status, 404);
    });
    await t.test('passes separate account routing, image and model to authenticated adapter', async () => {
      const result = await post('/api/video', payload);
      assert.equal(result.status, 200);
      assert.equal((await result.json()).base64, clip);
      const call = calls.at(-1);
      assert.equal(call.path, '/video'); assert.equal(call.auth, 'Bearer test-bridge-secret');
      assert.deepEqual(call.body, { accountId: 7, prompt: payload.prompt, modelDisplayName: payload.model, aspectRatio: '9:16', durationSeconds: 6, resolution: '720p', referenceImage: { base64: 'aGVsbG8=', mimeType: 'image/png' } });
    });
    await t.test('rejects invalid account/model constraints and cross-origin writes before adapter', async () => {
      const count = calls.length;
      assert.equal((await post('/api/video', { ...payload, accountId: 11 })).status, 400);
      assert.equal((await post('/api/video', { ...payload, model: 'Veo 3.1 - Fast', duration: 4 })).status, 400);
      assert.equal((await post('/api/video', payload, { Origin: 'https://other-site.example' })).status, 403);
      assert.equal(calls.length, count);
    });
    await t.test('routes enhancement to text endpoint', async () => {
      const result = await post('/api/text', { accountId: 2, prompt: 'Enhance this scene' });
      assert.equal((await result.json()).text, 'A cinematic scene in English.');
      assert.equal(calls.at(-1).path, '/text'); assert.equal(calls.at(-1).body.accountId, 2);
    });
    await t.test('preserves credit error code and redacts adapter secret', async () => {
      adapterMode = 'error';
      const result = await post('/api/video', payload);
      assert.equal(result.status, 429);
      const { error } = await result.json();
      assert.match(error, /429 quota exhausted/); assert.equal(error.includes('test-bridge-secret'), false);
      adapterMode = 'ok';
    });
    await t.test('prevents parallel generation through the local server', async () => {
      adapterMode = 'wait';
      const first = post('/api/video', payload);
      for (let i = 0; !release && i < 100; i++) await new Promise(r => setTimeout(r, 10));
      assert.ok(release);
      const next = await post('/api/video', payload);
      assert.equal(next.status, 409);
      release(); adapterMode = 'ok';
      assert.equal((await first).status, 200);
    });
  } finally { child.kill('SIGTERM'); adapter.closeAllConnections(); await new Promise(resolve => adapter.close(resolve)); }
});
