'use strict';

// Run a Studio server first, then: node tests/browser_microphone.cjs
// Uses Chromium's synthetic microphone, never a physical device.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');

const baseURL = process.env.HMONG_STUDIO_URL || 'http://127.0.0.1:8094';
const executablePath = process.env.CHROMIUM_PATH || '/usr/bin/chromium';

async function main() {
  const browser = await chromium.launch({
    executablePath,
    headless: true,
    args: ['--no-sandbox', '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'],
  });
  const results = [];

  async function run(name, test, setup, url = baseURL) {
    const context = await browser.newContext({ permissions: ['microphone'] });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.addInitScript(() => {
      window.__microphoneTest = { requests: 0, streams: [], dataEvents: 0 };
      if (navigator.mediaDevices?.getUserMedia) {
        const getUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
        navigator.mediaDevices.getUserMedia = async constraints => {
          window.__microphoneTest.requests++;
          const stream = await getUserMedia(constraints);
          window.__microphoneTest.streams.push(stream);
          return stream;
        };
      }
      if (window.MediaRecorder) {
        const OriginalRecorder = window.MediaRecorder;
        window.MediaRecorder = class extends OriginalRecorder {
          constructor(...args) {
            super(...args);
            this.addEventListener('dataavailable', () => window.__microphoneTest.dataEvents++);
          }
        };
      }
    });
    try {
      if (setup) await setup(page);
      await page.goto(url, { waitUntil: 'networkidle' });
      // The microphone lives in an optional, initially collapsed panel.
      await page.locator('#record').evaluate(button => { button.closest('details').open = true; });
      await test(page);
      assert.deepEqual(errors, [], 'unexpected browser JavaScript errors');
      results.push({ name, passed: true });
      console.log(`PASS ${name}`);
    } catch (error) {
      results.push({ name, passed: false });
      console.error(`FAIL ${name}: ${error.stack || error}`);
    } finally {
      await context.close();
    }
  }

  async function assertReady(page) {
    assert.equal(await page.locator('#record').isEnabled(), true);
    assert.equal(await page.locator('#audioFile').isEnabled(), true);
    assert.match(await page.locator('#record').textContent(), /Thu mẫu mới/);
  }

  try {
    await run('selecting the supplied male/female references never requests a microphone', async page => {
      for (const voice of ['hmong-white-male', 'hmong-white-female']) {
        await page.selectOption('#voice', voice);
        assert.equal(await page.inputValue('#referenceVoice'), voice);
        assert.match(await page.locator('#referencePlayer').getAttribute('src'), new RegExp(`${voice}\\.mp3$`));
      }
      await page.selectOption('#referenceVoice', 'hmong-white-male');
      assert.equal(await page.inputValue('#voice'), 'hmong-white-male');
      assert.equal(await page.evaluate(() => window.__microphoneTest.requests), 0);
    });

    await run('a real MediaRecorder records, stops, decodes audio and releases all fake microphone tracks', async page => {
      await page.click('#record');
      await page.waitForFunction(() => document.getElementById('microphoneStatus').textContent.includes('Đang thu micro'));
      await page.waitForFunction(() => window.__microphoneTest.dataEvents > 0);
      await page.click('#record');
      await page.waitForFunction(() => document.getElementById('microphoneStatus').textContent.includes('Đã thu xong'));
      await page.waitForFunction(() => document.getElementById('player').duration > 0);
      assert.equal(await page.locator('#download').isEnabled(), true);
      assert.match(await page.locator('#audioInfo').textContent(), /[\d.]+ giây/);
      assert.match(await page.locator('#player').getAttribute('src'), /^blob:/);
      assert.equal(await page.locator('#audio').evaluate(element => element.open), true);
      assert.equal(await page.evaluate(() => window.__microphoneTest.requests), 1);
      assert.equal(await page.evaluate(() => window.__microphoneTest.streams.every(stream => stream.getTracks().every(track => track.readyState === 'ended'))), true);
      await assertReady(page);
    });

    for (const [errorName, expected] of [
      ['NotAllowedError', /Micro chưa được cấp quyền/],
      ['NotFoundError', /Không tìm thấy micro/],
      ['NotReadableError', /Micro có thể đang được ứng dụng khác sử dụng/],
    ]) {
      await run(`${errorName} shows specific recovery guidance and restores controls`, async page => {
        await page.click('#record');
        await page.waitForFunction(() => !document.getElementById('record').disabled);
        assert.match(await page.locator('#microphoneStatus').textContent(), expected);
        await assertReady(page);
      }, page => page.addInitScript(name => {
        navigator.mediaDevices.getUserMedia = async () => {
          window.__microphoneTest.requests++;
          throw new DOMException('Deliberate microphone failure for regression testing', name);
        };
      }, errorName));
    }

    await run('MediaRecorder NotSupportedError is distinct from permission denial and releases the opened stream', async page => {
      await page.click('#record');
      await page.waitForFunction(() => !document.getElementById('record').disabled);
      assert.match(await page.locator('#microphoneStatus').textContent(), /không hỗ trợ định dạng thu âm/);
      assert.equal(await page.evaluate(() => window.__microphoneTest.streams.length), 1);
      assert.equal(await page.evaluate(() => window.__microphoneTest.streams.every(stream => stream.getTracks().every(track => track.readyState === 'ended'))), true);
      await assertReady(page);
    }, page => page.addInitScript(() => {
      window.MediaRecorder = class {
        static isTypeSupported() { return true; }
        constructor() { throw new DOMException('Deliberate unsupported recorder', 'NotSupportedError'); }
      };
    }));

    await run('skipping pending permission restores controls and releases a stream granted later', async page => {
      await page.click('#record');
      assert.equal(await page.locator('#record').isDisabled(), true);
      assert.equal(await page.locator('#audioFile').isDisabled(), true);
      await page.click('#skipMicrophone');
      await assertReady(page);
      assert.match(await page.locator('#microphoneStatus').textContent(), /Đã bỏ qua micro/);
      await page.evaluate(() => window.__resolveMicrophone());
      await page.waitForFunction(() => window.__lateTrackStops === 1);
      assert.equal(await page.evaluate(() => window.__unexpectedRecorderStarts), 0);
      assert.match(await page.locator('#microphoneStatus').textContent(), /Đã bỏ qua micro/);
      assert.equal(await page.locator('#download').isDisabled(), true);
      await assertReady(page);
    }, page => page.addInitScript(() => {
      window.__lateTrackStops = 0;
      window.__unexpectedRecorderStarts = 0;
      navigator.mediaDevices.getUserMedia = () => {
        window.__microphoneTest.requests++;
        return new Promise(resolve => {
          window.__resolveMicrophone = () => resolve({
            getTracks: () => [{ stop: () => window.__lateTrackStops++ }],
          });
        });
      };
      window.MediaRecorder = class {
        constructor() { window.__unexpectedRecorderStarts++; }
      };
    }));

    const insecureURL = 'http://hmong-studio.test';
    await run('a genuine insecure HTTP origin explains localhost versus remote HTTPS before requesting a microphone', async page => {
      assert.equal(await page.evaluate(() => window.isSecureContext), false);
      await page.click('#record');
      assert.match(await page.locator('#microphoneStatus').textContent(), /chặn micro trên kết nối HTTP/);
      assert.match(await page.locator('#microphoneStatus').textContent(), /truy cập từ máy khác cần HTTPS/);
      assert.equal(await page.evaluate(() => window.__microphoneTest.requests), 0);
      await assertReady(page);
    }, page => page.route(`${insecureURL}/**`, async route => {
      const requested = new URL(route.request().url());
      const target = new URL(requested.pathname + requested.search, baseURL);
      const response = await route.fetch({ url: target.href });
      await route.fulfill({ response });
    }), insecureURL);
  } finally {
    await browser.close();
  }

  const failed = results.filter(result => !result.passed);
  console.log(`${results.length - failed.length}/${results.length} browser microphone checks passed`);
  if (failed.length) process.exitCode = 1;
}

main().catch(error => { console.error(error); process.exitCode = 1; });
