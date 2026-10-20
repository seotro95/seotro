'use strict';

// Run: node tests/browser_ultra.cjs. This serves static UI and mocks API job
// states. It validates browser behavior, never measures TTS/GPU performance.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');

async function main() {
  const root = path.resolve(__dirname, '..');
  const wav = fs.readFileSync(path.join(root, 'examples/hmong-female-test.wav'));
  const mp3 = fs.readFileSync(path.join(root, 'static/voices/hmong-white-female.mp3'));
  let mp3Requests = 0;
  const server = http.createServer((request, response) => {
    const url = new URL(request.url, 'http://localhost'), relative = url.pathname;
    // Chromium's native downloads can bypass page.route; serve the mock audio
    // here as well, then verify download completion and exact file bytes.
    if (relative.startsWith('/api/speech/jobs/') && relative.endsWith('/audio')) {
      const asMP3 = url.searchParams.get('format') === 'mp3';
      if (asMP3) mp3Requests++;
      response.writeHead(200, { 'Content-Type': asMP3 ? 'audio/mpeg' : 'audio/wav',
        'Content-Disposition': 'attachment; filename="voice.' + (asMP3 ? 'mp3' : 'wav') + '"' });
      response.end(asMP3 ? mp3 : wav); return;
    }
    const filename = path.resolve(root, '.' + (relative === '/' ? '/static/index.html' : relative));
    if (!filename.startsWith(root + path.sep) || !fs.existsSync(filename) || !fs.statSync(filename).isFile()) {
      response.writeHead(404).end(); return;
    }
    const types = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.mp3': 'audio/mpeg' };
    response.writeHead(200, { 'Content-Type': types[path.extname(filename)] || 'application/octet-stream' });
    fs.createReadStream(filename).pipe(response);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = 'http://127.0.0.1:' + server.address().port;
  let browser;
  try {
    browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium', headless: true, args: ['--no-sandbox'] });
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, acceptDownloads: true });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('dialog', dialog => dialog.accept());
    let state = null, posted = null, polls = 0, pauses = 0, resumes = 0;
    await page.addInitScript(() => {
      window.__audioFetches = [];
      const actual = window.fetch.bind(window);
      window.fetch = (input, ...rest) => {
        const url = typeof input === 'string' ? input : input.url;
        if (url.includes('/audio')) window.__audioFetches.push(url);
        return actual(input, ...rest);
      };
    });
    await page.route('**/api/**', async route => {
      const request = route.request(), url = new URL(request.url()), pathname = url.pathname;
      const json = body => route.fulfill({ json: body });
      if (pathname === '/api/status') return json({ message: 'Sẵn sàng', local_cloning: true, custom_cloning: true, clone_styles: ['neutral', 'review'], emotions: true, cosy: { device: 'auto' }, local: { dependencies: true, tts_models: { mww: true } } });
      if (pathname === '/api/clones') return json({ voices: [] });
      if (pathname === '/api/speech/jobs') { posted = request.postDataJSON(); return json(state); }
      if (pathname.endsWith('/pause')) { pauses++; state = { ...state, pause_requested: true }; return json(state); }
      if (pathname.endsWith('/resume')) { resumes++; state = { ...state, status: 'running', phase: 'synthesizing', pause_requested: false }; return json(state); }
      if (pathname.endsWith('/stop')) { state = { ...state, status: 'cancelled', phase: 'cancelled', pause_requested: false }; return json(state); }
      if (pathname.endsWith('/audio')) {
        const asMP3 = url.searchParams.get('format') === 'mp3';
        if (asMP3) mp3Requests++;
        return route.fulfill({ contentType: asMP3 ? 'audio/mpeg' : 'audio/wav', body: asMP3 ? mp3 : wav, headers: { 'Content-Disposition': 'attachment; filename="voice.' + (asMP3 ? 'mp3' : 'wav') + '"' } });
      }
      polls++; return json(state);
    });
    await page.goto(base);
    await page.waitForFunction(() => document.querySelector('#cloneState').textContent.includes('CosyVoice'));
    const text = 'Kuv twb hais qhia rau koj. Hmoob Dawb: kuv, koj, nws, peb, nej, lawv.';
    await page.fill('#text', text);
    await page.selectOption('#computeMode', 'ultra');
    assert.match(await page.textContent('#computeHelp'), /dùng lại các đoạn/);
    await page.click('#save');
    assert.equal(await page.evaluate(() => JSON.parse(localStorage.getItem('hmong-projects'))[0].compute_mode), 'ultra');
    const project = { version: 1, title: 'Ultra', text, dialect: 'mww', voice: 'hmong-white-female', emotion: 'review', speed: 1, compute_mode: 'ultra', cleanup: 'light' };
    await page.locator('#projectFile').setInputFiles({ name: 'ultra.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(project)) });
    await page.waitForFunction(() => document.querySelector('#title').value === 'Ultra');
    assert.equal(await page.inputValue('#text'), text);
    assert.equal(await page.locator('#mp3Download').isDisabled(), true);
    state = { id: 'ultra-job', status: 'running', phase: 'synthesizing', progress: 25, completed_units: 1, total_units: 4, elapsed_seconds: 12, estimated_total_seconds: null, eta_seconds: null, speed_multiplier: null, active_workers: 1, batch_size: 1, cache_hits: 0, runtime: { device: 'cuda:0', precision: 'float32' } };
    await page.click('#ultraGenerate');
    await page.waitForFunction(() => !document.querySelector('#pauseGenerate').disabled);
    assert.equal(posted.compute_mode, 'ultra'); assert.equal(posted.text, text);
    assert.equal(await page.textContent('#metricSpeed'), 'Đang đo');
    assert.equal(await page.textContent('#metricDuration'), 'Chưa đủ dữ liệu');
    assert.equal(await page.textContent('#metricRuntime'), 'GPU NVIDIA');
    assert.equal(await page.textContent('#metricWorkers'), '1');
    assert.equal(await page.textContent('#metricCurrent'), '2 / 4');
    assert.equal(await page.locator('#text').isDisabled(), true);
    console.log('PASS ULTRA project roundtrip and exact Hmong script, real metric placeholders, no premature MP3');

    await page.click('#pauseGenerate');
    await page.waitForFunction(() => document.querySelector('#generationDetail').textContent.includes('Đang chờ hết đoạn'));
    assert.equal(pauses, 1);
    assert.equal(await page.locator('#stopGenerate').isEnabled(), true);
    const pendingPolls = polls;
    state = { ...state, status: 'paused', phase: 'paused', active_workers: 0, estimated_total_seconds: 80, eta_seconds: 36, speed_multiplier: 1.5, cache_hits: 2 };
    await page.waitForFunction(() => document.querySelector('#generationDetail').textContent.startsWith('Đã tạm dừng'));
    await page.waitForTimeout(900);
    assert.ok(polls > pendingPolls);
    assert.equal(await page.locator('#generate').isDisabled(), true);
    assert.equal(await page.locator('#ultraGenerate').isDisabled(), true);
    assert.equal(await page.locator('#resumeGenerate').isEnabled(), true);
    assert.equal(await page.textContent('#metricDuration'), '1:20');
    assert.equal(await page.textContent('#metricETA'), '0:36');
    assert.equal(await page.textContent('#metricSpeed'), '1,5× thời gian thực');
    assert.equal(await page.textContent('#metricCache'), '2');
    assert.equal(await page.textContent('#metricCurrent'), 'Đã tạm dừng');
    await page.click('#resumeGenerate');
    await page.waitForFunction(() => !document.querySelector('#pauseGenerate').disabled);
    assert.equal(resumes, 1);
    assert.equal(await page.textContent('#generationPercent'), '25%');
    console.log('PASS cooperative pause request/ACK, continuous polling while paused, measured ETA/speed/cache, resume controls');

    state = { ...state, status: 'completed', phase: 'completed', progress: 100, completed_units: 4, audio_bytes: 200 * 1024 * 1024, active_workers: 0, eta_seconds: 0 };
    await page.waitForFunction(() => !document.querySelector('#generate').disabled);
    assert.equal(await page.textContent('#generationPercent'), '100%');
    assert.equal(await page.locator('#fullDownload').isEnabled(), true);
    assert.equal(await page.locator('#mp3Download').isEnabled(), true);
    assert.equal(await page.locator('#download').isDisabled(), true);
    assert.deepEqual(await page.evaluate(() => window.__audioFetches), []);
    const mp3Download = page.waitForEvent('download'); await page.click('#mp3Download');
    const mp3File = await mp3Download;
    assert.match(mp3File.suggestedFilename(), /\.mp3$/);
    assert.equal(await mp3File.failure(), null);
    assert.deepEqual(fs.readFileSync(await mp3File.path()), mp3);
    assert.equal(mp3Requests, 1);
    assert.deepEqual(await page.evaluate(() => window.__audioFetches), []);
    const wavDownload = page.waitForEvent('download'); await page.click('#fullDownload');
    const wavFile = await wavDownload;
    assert.match(wavFile.suggestedFilename(), /\.wav$/);
    assert.equal(await wavFile.failure(), null);
    assert.deepEqual(fs.readFileSync(await wavFile.path()), wav);
    const previous = await page.locator('#player').getAttribute('src');
    state = { id: 'paused-stop', status: 'paused', phase: 'paused', pause_requested: true, progress: 42, active_workers: 0 };
    await page.click('#generate');
    await page.waitForFunction(() => !document.querySelector('#stopGenerate').disabled);
    await page.click('#stopGenerate');
    await page.waitForFunction(() => !document.querySelector('#generate').disabled);
    assert.equal(await page.textContent('#generationPercent'), '42%');
    assert.equal(await page.locator('#player').getAttribute('src'), previous);
    assert.equal(await page.locator('#mp3Download').isEnabled(), true);
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    assert.deepEqual(errors, []);
    assert.doesNotMatch(await page.locator('body').textContent(), /đã đạt 30|đạt 2 phút/i);
    console.log('PASS native MP3/WAV download without large fetch/decode, Stop while paused preserves prior audio, mobile and no JS errors');
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
