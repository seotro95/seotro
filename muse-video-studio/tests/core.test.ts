import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseScript, extractEmails, normalizeSettings, DEFAULT_SETTINGS, restoreWorkspace, createScenes, errorInfo, resolveAccount, requestedDimensions, meetsResolution } from '../src/core.ts';

test('SRT removes BOM, timestamps, indices and formatting while keeping multiline scene text', () => {
  assert.deepEqual(parseScript('\uFEFF1\r\n00:00:00,000 --> 00:00:04,000\r\n<b>Cảnh một</b>\r\nHàng hai\r\n\r\n2\r\n00:00:04,000 --> 00:00:08,000\r\nCảnh hai'), ['Cảnh một Hàng hai', 'Cảnh hai']);
});
test('TXT parses paragraphs and numbered lines without silently dropping overflow scenes', () => {
  assert.deepEqual(parseScript('1. Một\n2. Hai\n\n3. Ba'), ['Một\n2. Hai', 'Ba']);
  assert.deepEqual(parseScript('1. Một\n2. Hai'), ['Một', 'Hai']);
  assert.equal(parseScript(Array.from({ length: 12 }, (_, i) => `Cảnh ${i}`).join('\n')).length, 12);
  assert.deepEqual(parseScript('   '), []);
});
test('bulk emails are deduplicated and limited to ten', () => {
  assert.deepEqual(extractEmails('Name <a@example.com> a@example.com; b+studio@example.org; bad@'), ['a@example.com', 'b+studio@example.org']);
  assert.equal(extractEmails(Array.from({ length: 12 }, (_, i) => `node${i}@example.com`).join('\n')).length, 10);
});
test('Veo keeps 8s while preserving requested HD/QHD/4K quality', () => {
  assert.equal(normalizeSettings({ ...DEFAULT_SETTINGS, model: 'Veo 3.1 - Lite' }).duration, 8);
  assert.equal(normalizeSettings({ ...DEFAULT_SETTINGS, model: 'Veo 3.1 - Fast' }).resolution, '720p');
  assert.equal(normalizeSettings({ ...DEFAULT_SETTINGS, model: 'Veo 3.1 - Fast', resolution: '4k' }).resolution, '4k');
  assert.equal(normalizeSettings({ ...DEFAULT_SETTINGS, duration: 10 }).duration, 10);
});
test('one verified account serves all unassigned slots but never overrides an explicit assignment', () => {
  for (const scene of createScenes()) assert.equal(resolveAccount(scene, [1], DEFAULT_SETTINGS), 1);
  assert.equal(resolveAccount({ id: 3, accountId: 2 }, [1], DEFAULT_SETTINGS), null);
  assert.equal(resolveAccount({ id: 3, accountId: 2 }, [1, 2], DEFAULT_SETTINGS), 2);
  assert.equal(resolveAccount({ id: 3, accountId: null }, [1, 2], { shareUnassigned: false, sharedAccountId: null }), null);
  assert.equal(resolveAccount({ id: 2, accountId: null }, [1, 2], { shareUnassigned: true, sharedAccountId: 1 }), 1);
  assert.equal(resolveAccount({ id: 2, accountId: null }, [2], { shareUnassigned: true, sharedAccountId: 1 }), null);
});
test('measured resolution distinguishes requested 2K/4K from lower-size output', () => {
  assert.deepEqual(requestedDimensions('4k', '9:16'), { width: 2160, height: 3840 });
  const image = { kind: 'image' as const, base64: '', url: '', mimeType: 'image/png', demo: false, requestedResolution: '4k' as const, aspectRatio: '16:9' as const, metadata: { width: 640, height: 360 } };
  assert.equal(meetsResolution(image), false);
  assert.equal(meetsResolution({ ...image, metadata: { width: 3840, height: 2160 } }), true);
  assert.equal(meetsResolution({ ...image, metadata: { width: 2160, height: 3840 } }), false);
  assert.equal(meetsResolution({ ...image, demo: true }), null);
});
test('workspace restore ignores stale videos, images, status and untrusted settings', () => {
  const scenes = createScenes().map(s => ({ ...s, video: { base64: 'fake' }, reference: { url: 'fake' }, status: 'running', prompt: 'restored' }));
  const restored = restoreWorkspace(JSON.stringify({ version: 1, scenes, settings: { model: 'made-up', duration: 90, mode: 'other' } }));
  assert.equal(restored.scenes[0].prompt, 'restored');
  assert.equal(restored.scenes[0].status, 'ready');
  assert.equal(restored.scenes[0].video, undefined);
  assert.equal(restored.scenes[0].reference, null);
  assert.equal(restored.settings.mode, 'muse');
  assert.equal(restored.settings.model, DEFAULT_SETTINGS.model);
  assert.equal(restoreWorkspace('{bad json').scenes.length, 10);
});
test('errors distinguish credit, filtering, service capacity and missing Muse integration', () => {
  assert.match(errorInfo(new Error('429 quota exhausted')).hint, /hạn mức/);
  assert.match(errorInfo('safety filter blocked').hint, /bộ lọc/);
  assert.match(errorInfo('503 overloaded').hint, /đang bận/);
  assert.match(errorInfo('MUSE_NOT_CONFIGURED').hint, /Muse AI/);
});
