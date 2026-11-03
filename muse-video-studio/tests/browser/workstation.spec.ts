import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';
import { readFile } from 'node:fs/promises';
const video = (await readFile(new URL('../../public/demo.mp4', import.meta.url))).toString('base64');
const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aO1sAAAAASUVORK5CYII=', 'base64');
test.beforeEach(async ({ page }) => { await page.goto('/'); });
async function configureAdapter(page: Page) {
  await page.route('**/api/status', route => route.fulfill({ json: { museConfigured: true, busy: false, credit: null, gpu: null } }));
  await page.reload();
}

test('matches 10-slot layout on desktop and remains within mobile viewport', async ({ page }) => {
  await page.setViewportSize({ width: 1433, height: 1000 });
  await expect(page.locator('.scene-card')).toHaveCount(10);
  expect(await page.locator('.scene-grid').evaluate(el => getComputedStyle(el).gridTemplateColumns.split(' ').length)).toBe(5);
  await expect(page.getByLabel('Model AI')).toHaveValue('Omni 1.1 Flash');
  await page.screenshot({ path: 'test-results/desktop.png', fullPage: true });
  await page.getByLabel('Model AI').selectOption('Veo 3.1 - Fast');
  await expect(page.getByLabel('Thời lượng')).toHaveValue('8');
  await expect(page.getByLabel('Chất lượng')).toHaveValue('720p');
  await expect(page.getByLabel('Thời lượng')).toBeDisabled();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/mobile.png', fullPage: true });
});

test('imports SRT, rejects overflow, preserves raw text, and persists prompts', async ({ page }) => {
  await page.getByRole('button', { name: 'Nhập TXT / SRT' }).click();
  await page.getByLabel('Nội dung TXT / SRT').fill(Array.from({ length: 11 }, (_, i) => `Scene ${i}`).join('\n'));
  await expect(page.getByRole('button', { name: 'Nạp vào Studio', exact: true })).toBeDisabled();
  await page.getByLabel('Nội dung TXT / SRT').fill('1\n00:00:00,000 --> 00:00:04,000\nCảnh một\n\n2\n00:00:04,000 --> 00:00:08,000\nCảnh hai');
  await page.getByRole('button', { name: 'Nạp vào Studio', exact: true }).click();
  await expect(page.getByLabel('Kịch bản cảnh 1', { exact: true })).toHaveValue('Cảnh một');
  await expect(page.getByLabel('Kịch bản cảnh 3', { exact: true })).toHaveValue('');
  await page.reload();
  await expect(page.getByLabel('Kịch bản cảnh 2', { exact: true })).toHaveValue('Cảnh hai');
});

test('global image sync, per-scene override and manual reapply', async ({ page }) => {
  const upload = async (button: string, name: string) => {
    const chooser = page.waitForEvent('filechooser');
    await page.getByRole('button', { name: button, exact: true }).click();
    await (await chooser).setFiles({ name, mimeType: 'image/png', buffer: png });
  };
  await upload('Tải ảnh nhân vật chung', 'global.png');
  await expect(page.locator('.scene-image')).toHaveCount(10);
  await upload('Đổi ảnh cảnh 1', 'private.png');
  await expect(page.getByTestId('scene-1').getByText('Ảnh riêng', { exact: false })).toBeVisible();
  await page.getByRole('button', { name: 'Áp dụng cho toàn bộ 10 tài khoản' }).click();
  await expect(page.getByTestId('scene-1').getByText('Ảnh chung · đã đồng bộ')).toBeVisible();
  await page.getByRole('button', { name: 'Gỡ ảnh cảnh 2', exact: true }).click();
  await expect(page.getByTestId('scene-2').locator('.scene-image')).toHaveCount(0);
  await page.getByTestId('scene-2').getByRole('button', { name: 'Dùng ảnh chung' }).click();
  await expect(page.locator('.scene-image')).toHaveCount(10);
});

test('Muse contract sends accountId, settings, R2V and modifier; video plays and downloads', async ({ page }) => {
  await configureAdapter(page);
  let payload: Record<string, any> = {};
  await page.route('**/api/video', async route => { payload = route.request().postDataJSON(); await route.fulfill({ json: { base64: video, mimeType: 'video/mp4' } }); });
  const chooser = page.waitForEvent('filechooser');
  await page.getByRole('button', { name: 'Tải ảnh nhân vật chung' }).click();
  await (await chooser).setFiles({ name: 'ref.png', mimeType: 'image/png', buffer: png });
  await expect(page.locator('.scene-image')).toHaveCount(10);
  await page.getByRole('button', { name: '10 Tài khoản Muse', exact: true }).click();
  await page.getByLabel('Chỉ thị chất lượng toàn cục', { exact: false }).fill('cinematic lighting');
  await page.getByRole('button', { name: 'Hoàn tất', exact: true }).click();
  await page.getByTestId('scene-2').getByRole('button', { name: 'Tạo cảnh này' }).click();
  await expect(page.getByTestId('scene-2').locator('video')).toBeVisible();
  expect(payload.accountId).toBe(2);
  expect(payload.prompt).toContain('cinematic lighting');
  expect(payload.image.mimeType).toBe('image/png');
  expect(payload.model).toBe('Omni 1.1 Flash');
  await expect.poll(async () => page.getByTestId('scene-2').locator('video').evaluate((v: HTMLVideoElement) => v.readyState)).toBeGreaterThan(0);
  expect(await page.getByTestId('scene-2').locator('video').evaluate((v: HTMLVideoElement) => v.duration)).toBeCloseTo(4, 0);
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Tải cảnh 2', exact: true }).click();
  expect((await download).suggestedFilename()).toBe('scene-02.mp4');
  await page.getByLabel('Kịch bản cảnh 2', { exact: true }).fill('Changed prompt');
  await expect(page.getByTestId('scene-2').locator('video')).toHaveCount(0);
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0');
});

test('batch respects disabled accounts, shows failures, and never overlaps render requests', async ({ page }) => {
  await configureAdapter(page);
  const calls: number[] = []; let active = 0; let peak = 0;
  await page.route('**/api/video', async route => {
    const id = route.request().postDataJSON().accountId; calls.push(id); active++; peak = Math.max(peak, active);
    await new Promise(r => setTimeout(r, 75)); active--;
    await route.fulfill(id === 3 ? { status: 429, json: { error: '429 quota exceeded' } } : { json: { base64: video, mimeType: 'video/mp4' } });
  });
  await page.getByRole('button', { name: '10 Tài khoản Muse', exact: true }).click();
  await page.locator('.account-list input[type=checkbox]').nth(1).uncheck();
  await page.getByRole('button', { name: 'Hoàn tất', exact: true }).click();
  await page.getByRole('button', { name: 'CHẠY TOÀN BỘ 10 VIDEO' }).click();
  await expect(page.getByRole('button', { name: 'CHẠY TOÀN BỘ 10 VIDEO' })).toBeVisible();
  expect(calls).toEqual([1, 3, 4, 5, 6, 7, 8, 9, 10]); expect(peak).toBe(1);
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '8');
  await expect(page.getByTestId('scene-3').getByText('Kiểm tra hạn mức', { exact: false })).toBeVisible();
  await page.getByTestId('scene-3').getByText('Mã lỗi gốc').click();
  await expect(page.getByTestId('scene-3').locator('pre')).toContainText('429 quota exceeded');
});

test('demo batch can be stopped and resumed; test clips are labelled', async ({ page }) => {
  await page.getByRole('button', { name: 'Chẩn đoán API', exact: true }).click();
  await page.getByLabel('Kết nối tạo video', { exact: true }).selectOption('demo');
  await page.getByRole('button', { name: 'Đóng', exact: true }).last().click();
  await page.getByRole('button', { name: 'CHẠY TOÀN BỘ 10 VIDEO' }).click();
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '1');
  await page.getByRole('button', { name: 'Dừng hàng đợi' }).click();
  await expect(page.getByRole('button', { name: 'CHẠY TOÀN BỘ 10 VIDEO' })).toBeVisible();
  const count = await page.locator('.scene-card video').count();
  expect(count).toBeGreaterThan(0); expect(count).toBeLessThan(10);
  await expect(page.locator('.preview-label').first()).toHaveText('CLIP KIỂM THỬ');
  await page.getByRole('button', { name: 'CHẠY TOÀN BỘ 10 VIDEO' }).click();
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '10', { timeout: 15000 });
});

test('missing integration is explained before render and sends no doomed AI requests', async ({ page }) => {
  const requests: string[] = [];
  page.on('request', request => { if (/\/api\/(video|text)$/.test(request.url())) requests.push(request.url()); });
  await expect(page.getByRole('region', { name: 'Cần kết nối tạo video' })).toContainText('Chưa có kết nối tạo video AI');
  await expect(page.getByTestId('scene-1').getByRole('button', { name: 'Tạo cảnh này' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'CHẠY TOÀN BỘ 10 VIDEO' })).toBeDisabled();
  await expect(page.getByTestId('scene-1').getByRole('button', { name: 'AI Enhance' })).toBeDisabled();
  await expect(page.locator('video')).toHaveCount(0);
  await page.getByRole('button', { name: 'Xem cách kết nối' }).click();
  await expect(page.getByRole('heading', { name: 'Cần gì để tạo video thật?' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Mở trang tài khoản Muse.ai' })).toHaveAttribute('href', 'https://muse.ai/');
  await expect(page.locator('#provider-mode option')).toHaveCount(2);
  expect(await page.locator('#provider-mode option').evaluateAll(options => options.map(option => (option as HTMLOptionElement).value))).toEqual(['muse', 'demo']);
  await expect(page.getByRole('button', { name: 'Kiểm tra render thực tế' })).toBeDisabled();
  expect(requests).toEqual([]);
});

test('Enhance uses the scene account; diagnostic never renders without explicit consent', async ({ page }) => {
  await configureAdapter(page);
  let textPayload: any; let renders = 0; let videoPayload: any;
  await page.route('**/api/text', async route => { textPayload = route.request().postDataJSON(); await route.fulfill({ json: { text: 'Cinematic tracking shot through an ancient temple at sunrise.' } }); });
  await page.route('**/api/video', async route => { renders++; videoPayload = route.request().postDataJSON(); await route.fulfill({ json: { base64: video, mimeType: 'video/mp4' } }); });
  await page.getByTestId('scene-4').getByRole('button', { name: 'AI Enhance' }).click();
  await expect(page.getByLabel('Kịch bản cảnh 4', { exact: true })).toHaveValue('Cinematic tracking shot through an ancient temple at sunrise.');
  expect(textPayload.accountId).toBe(4);
  expect(textPayload.prompt).toContain('Rewrite this scene');
  await page.getByRole('button', { name: 'Chẩn đoán API', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Kiểm tra render thực tế' })).toBeDisabled();
  expect(renders).toBe(0);
  await page.getByRole('checkbox', { name: 'Tôi đồng ý gửi một yêu cầu render thử', exact: false }).check();
  await page.getByRole('button', { name: 'Kiểm tra render thực tế' }).click();
  await expect(page.locator('.diagnostic-result')).toContainText('hoàn tất');
  expect(renders).toBe(1);
  expect(videoPayload.duration).toBe(4); expect(videoPayload.resolution).toBe('360p');
  await expect(page.locator('.diagnostic-result')).toContainText('API không cung cấp');
});

test('refreshing a newly configured adapter enables rendering without losing the script', async ({ page }) => {
  await page.getByLabel('Kịch bản cảnh 1', { exact: true }).fill('Keep this script while connecting.');
  await page.getByRole('button', { name: 'Xem cách kết nối' }).click();
  await page.route('**/api/status', route => route.fulfill({ json: { museConfigured: true, busy: false, credit: null, gpu: null } }));
  await page.getByRole('button', { name: 'Đọc cấu hình', exact: true }).click();
  await expect(page.locator('.setup-help')).toHaveCount(0);
  await page.getByRole('button', { name: 'Đóng', exact: true }).last().click();
  await expect(page.getByRole('button', { name: 'CHẠY TOÀN BỘ 10 VIDEO' })).toBeEnabled();
  await expect(page.getByLabel('Kịch bản cảnh 1', { exact: true })).toHaveValue('Keep this script while connecting.');
});
