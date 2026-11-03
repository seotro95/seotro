import { test } from 'node:test';
import assert from 'node:assert/strict';
import { browserCommand } from '../browser.mjs';

test('Windows opens the local URL without shell quoting or a PowerShell script', () => {
  assert.deepEqual(browserCommand('http://127.0.0.1:8788', 'win32', 'C:\\Windows'), ['C:\\Windows\\System32\\rundll32.exe', ['url.dll,FileProtocolHandler', 'http://127.0.0.1:8788/']]);
});
test('macOS and Linux receive the same ready server URL', () => {
  assert.deepEqual(browserCommand('http://127.0.0.1:9876', 'darwin'), ['open', ['http://127.0.0.1:9876/']]);
  assert.deepEqual(browserCommand('http://127.0.0.1:9876', 'linux'), ['xdg-open', ['http://127.0.0.1:9876/']]);
});
test('refuses to open an external site or an authenticated URL', () => {
  assert.throws(() => browserCommand('https://example.com', 'win32'));
  assert.throws(() => browserCommand('http://user:password@127.0.0.1:8788', 'win32'));
});
