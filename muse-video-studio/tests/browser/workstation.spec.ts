import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';
import { readFile } from 'node:fs/promises';
const video = (await readFile(new URL('../../public/demo.mp4', import.meta.url))).toString('base64');
const image = (await readFile(new URL('../../public/demo-image.png', import.meta.url))).toString('base64');
const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aO1sAAAAASUVORK5CYII=', 'base64');
test.beforeEach(async ({ page }) => { await page.goto('/'); });
async function configureAdapter(page: Page) {
  await page.route('**/api/status', route => route.fulfill({ json: { museConfigured: true, transport: 'adapter', accounts: [], busy: false, credit: null, gpu: null } }));
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
  await page.getByLabel('Chất lượng').selectOption('4k');
  await expect(page.getByLabel('Chất lượng')).toHaveValue('4k');
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
  await page.getByRole('button', { name: 'Áp dụng cho 10 cảnh' }).click();
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
  await page.getByRole('button', { name: 'Tài khoản Muse', exact: true }).click();
  await page.getByLabel('Chỉ thị chất lượng toàn cục', { exact: false }).fill('cinematic lighting');
  await page.getByRole('button', { name: 'Hoàn tất', exact: true }).click();
  await page.getByTestId('scene-2').getByRole('button', { name: 'Tạo cảnh này' }).click();
  await expect(page.getByTestId('scene-2').locator('video')).toBeVisible();
  expect(payload.accountId).toBe(1);
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

test('batch runs enabled scenes concurrently and keeps per-scene failures', async ({ page }) => {
  test.setTimeout(60000);
  await configureAdapter(page);
  const calls: number[] = []; let active = 0; let peak = 0;
  const barrier: (() => void)[] = [];
  await page.route('**/api/video', async route => {
    const id = route.request().postDataJSON().accountId; calls.push(id); const index = calls.length; active++; peak = Math.max(peak, active);
    await new Promise<void>(resolve => barrier.push(resolve)); active--;
    await route.fulfill(index === 2 ? { status: 429, json: { error: '429 quota exceeded' } } : { json: { base64: video, mimeType: 'video/mp4' } });
  });
  await page.getByRole('checkbox', { name: 'Bật cảnh 2', exact: true }).uncheck();
  await page.getByRole('button', { name: 'TẠO 10 VIDEO' }).click();
  await expect.poll(() => calls.length).toBe(9);
  await expect(page.locator('.status-badge.running')).toHaveCount(9);
  expect(peak).toBe(9);
  for (const release of barrier) release();
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '8', { timeout: 20000 });
  await expect(page.getByRole('button', { name: 'TẠO 10 VIDEO' })).toBeVisible({ timeout: 10000 });
  expect(calls).toEqual(Array(9).fill(1)); expect(peak).toBe(9);
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '8');
  await expect(page.getByTestId('scene-3').getByText('Kiểm tra hạn mức', { exact: false })).toBeVisible();
  await page.getByTestId('scene-3').getByText('Mã lỗi gốc').click();
  await expect(page.getByTestId('scene-3').locator('pre')).toContainText('429 quota exceeded');
});

test('demo batch can be stopped and resumed; test clips are labelled', async ({ page }) => {
  await page.getByRole('button', { name: 'Chẩn đoán API', exact: true }).click();
  await page.getByLabel('Kết nối tạo video', { exact: true }).selectOption('demo');
  await page.getByRole('button', { name: 'Đóng', exact: true }).last().click();
  await page.getByTestId('scene-1').getByRole('button', { name: 'Tạo cảnh này', exact: true }).click();
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '1');
  await expect(page.getByRole('button', { name: 'TẠO 10 VIDEO' })).toBeVisible();
  await page.getByRole('button', { name: 'TẠO 10 VIDEO' }).click();
  await expect(page.locator('.status-badge.running')).toHaveCount(9);
  await page.getByRole('button', { name: 'Dừng tất cả luồng' }).click();
  await expect(page.getByRole('button', { name: 'TẠO 10 VIDEO' })).toBeVisible();
  await expect(page.locator('.status-badge.queued')).toHaveCount(0);
  const count = await page.locator('.scene-card video').count();
  expect(count).toBeGreaterThan(0); expect(count).toBeLessThan(10);
  await expect(page.locator('.preview-label').first()).toHaveText('CLIP KIỂM THỬ');
  await page.getByRole('button', { name: 'TẠO 10 VIDEO' }).click();
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '10', { timeout: 15000 });
});

test('missing integration is explained before render and sends no doomed AI requests', async ({ page }) => {
  const requests: string[] = [];
  page.on('request', request => { if (/\/api\/(video|text)$/.test(request.url())) requests.push(request.url()); });
  await expect(page.getByRole('region', { name: 'Cần kết nối tạo video' })).toContainText('Đăng nhập một tài khoản Muse');
  await expect(page.getByTestId('scene-1').getByRole('button', { name: 'Tạo cảnh này' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'TẠO 10 VIDEO' })).toBeDisabled();
  await expect(page.getByTestId('scene-1').getByRole('button', { name: 'AI Enhance' })).toBeDisabled();
  await expect(page.locator('video')).toHaveCount(0);
  await page.getByRole('button', { name: 'Kết nối tài khoản Muse', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Tài khoản Muse duy nhất' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Mở cửa sổ Muse', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Hoàn tất', exact: true }).click();
  await page.getByRole('button', { name: 'Chẩn đoán API', exact: true }).click();
  await expect(page.locator('#provider-mode option')).toHaveCount(2);
  expect(await page.locator('#provider-mode option').evaluateAll(options => options.map(option => (option as HTMLOptionElement).value))).toEqual(['muse', 'demo']);
  await expect(page.getByRole('button', { name: 'Kiểm tra render thực tế' })).toBeDisabled();
  expect(requests).toEqual([]);
});

test('Enhance uses the single Muse account; diagnostic never renders without explicit consent', async ({ page }) => {
  await configureAdapter(page);
  let textPayload: any; let renders = 0; let videoPayload: any;
  await page.route('**/api/text', async route => { textPayload = route.request().postDataJSON(); await route.fulfill({ json: { text: 'Cinematic tracking shot through an ancient temple at sunrise.' } }); });
  await page.route('**/api/video', async route => { renders++; videoPayload = route.request().postDataJSON(); await route.fulfill({ json: { base64: video, mimeType: 'video/mp4' } }); });
  await page.getByTestId('scene-4').getByRole('button', { name: 'AI Enhance' }).click();
  await expect(page.getByLabel('Kịch bản cảnh 4', { exact: true })).toHaveValue('Cinematic tracking shot through an ancient temple at sunrise.');
  expect(textPayload.accountId).toBe(1);
  expect(textPayload.prompt).toContain('Rewrite this scene');
  await page.getByRole('button', { name: 'Chẩn đoán API', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Kiểm tra render thực tế' })).toBeDisabled();
  expect(renders).toBe(0);
  await page.getByRole('checkbox', { name: 'Tôi đồng ý gửi một yêu cầu render thử', exact: false }).check();
  await page.getByRole('button', { name: 'Kiểm tra render thực tế' }).click();
  await expect(page.locator('.diagnostic-result')).toContainText('hoàn tất');
  expect(renders).toBe(1);
  expect(videoPayload.duration).toBe(4); expect(videoPayload.resolution).toBe('360p');
  await expect(page.locator('.diagnostic-result')).toContainText('GPU: chưa có thông tin');
});

test('refreshing a newly configured adapter enables rendering without losing the script', async ({ page }) => {
  await page.getByLabel('Kịch bản cảnh 1', { exact: true }).fill('Keep this script while connecting.');
  await page.getByRole('button', { name: 'Chẩn đoán API', exact: true }).click();
  await page.route('**/api/status', route => route.fulfill({ json: { museConfigured: true, transport: 'adapter', accounts: [], busy: false, credit: null, gpu: null } }));
  await page.getByRole('button', { name: 'Đọc cấu hình', exact: true }).click();
  await expect(page.locator('.setup-help')).toHaveCount(0);
  await page.getByRole('button', { name: 'Đóng', exact: true }).last().click();
  await expect(page.getByRole('button', { name: 'TẠO 10 VIDEO' })).toBeEnabled();
  await expect(page.getByLabel('Kịch bản cảnh 1', { exact: true })).toHaveValue('Keep this script while connecting.');
});

test('one login and one button create all ten videos using the same Muse account', async ({ page }) => {
  const account = { id: 1, state: 'disconnected', authenticated: false, active: false, checkedAt: null as string | null };
  await page.route('**/api/status', route => route.fulfill({ json: { museConfigured: true, transport: 'browser', accounts: [account], busy: false } }));
  await page.route('**/api/account/connect', route => { account.state = 'login_open'; account.active = true; return route.fulfill({ json: { accounts: [account] } }); });
  await page.route('**/api/account/check', route => { Object.assign(account, { state: 'ready', authenticated: true, checkedAt: new Date().toISOString() }); return route.fulfill({ json: { accounts: [account] } }); });
  const calls: number[] = [];
  await page.route('**/api/video', route => { calls.push(route.request().postDataJSON().accountId); return route.fulfill({ json: { base64: video, mimeType: 'video/mp4', metadata: { duration: 4, width: 640, height: 360 } } }); });
  await page.reload();
  await page.getByRole('button', { name: 'Kết nối Muse', exact: true }).click();
  await expect(page.locator('.single-account-controls')).toContainText('Chờ đăng nhập');
  await page.getByRole('button', { name: 'Kiểm tra phiên', exact: true }).click();
  await expect(page.locator('.single-account-controls')).toContainText('Đã xác minh');
  await expect(page.locator('.scene-account-picker, .account-inline, .account-list')).toHaveCount(0);
  await page.getByRole('button', { name: 'TẠO 10 VIDEO', exact: true }).click();
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '10', { timeout: 20000 });
  expect(calls).toEqual(Array(10).fill(1));
  await expect(page.getByTestId('scene-1').locator('.video-metadata')).toHaveText('Muse trả về: 640×360 · 4.0 giây');
  account.authenticated = false; account.state = 'login_open';
  await page.getByRole('button', { name: 'Chẩn đoán API', exact: true }).click();
  await page.getByRole('button', { name: 'Đọc cấu hình', exact: true }).click();
  await page.getByRole('button', { name: 'Đóng', exact: true }).last().click();
  await expect(page.getByTestId('scene-1').getByRole('button', { name: 'Tạo lại cảnh' })).toBeDisabled();
  await expect(page.locator('.scene-card video')).toHaveCount(10);
});

test('one click starts all ten image requests before any result on one verified session', async ({ page }) => {
  const account = { id: 1, state: 'ready', authenticated: true, active: true, checkedAt: null };
  await page.route('**/api/status', route => route.fulfill({ json: { museConfigured: true, transport: 'browser', accounts: [account], busy: false } }));
  const calls: number[] = [];
  const pending: (() => Promise<void>)[] = [];
  await page.route('**/api/image', async route => { calls.push(route.request().postDataJSON().accountId); await new Promise<void>(resolve => pending.push(async () => { await route.fulfill({ json: { base64: image, mimeType: 'image/png' } }); resolve(); })); });
  await page.reload();
  await page.getByRole('button', { name: 'Tạo ảnh hàng loạt', exact: true }).click();
  await page.getByRole('button', { name: 'TẠO 10 ẢNH', exact: true }).click();
  await expect.poll(() => calls.length).toBe(10);
  await expect(page.locator('.status-badge.running')).toHaveCount(10);
  await expect(page.locator('.generated-image')).toHaveCount(0);
  await Promise.all(pending.map(release => release()));
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '10', { timeout: 20000 });
  await expect(page.locator('.generated-image')).toHaveCount(10);
  expect(calls).toEqual(Array(10).fill(1));
  await expect(page.locator('.scene-account-picker, #shared-account, #email-bulk')).toHaveCount(0);
});

test('legacy account choices cannot route any of the ten scenes to another account', async ({ page }) => {
  await page.evaluate(() => localStorage.setItem('muse-workstation-v1', JSON.stringify({ version: 1, settings: { shareUnassigned: false, sharedAccountId: 8 }, scenes: Array.from({ length: 10 }, (_, i) => ({ prompt: `Legacy scene ${i + 1}`, accountId: i + 1, email: `old${i}@example.com`, enabled: true })) })));
  await configureAdapter(page);
  const calls: number[] = [];
  await page.route('**/api/video', route => { calls.push(route.request().postDataJSON().accountId); return route.fulfill({ json: { base64: video, mimeType: 'video/mp4' } }); });
  await expect(page.getByLabel('Kịch bản cảnh 10', { exact: true })).toHaveValue('Legacy scene 10');
  await expect(page.locator('.scene-account-picker, #shared-account, #email-bulk')).toHaveCount(0);
  await page.getByRole('button', { name: 'TẠO 10 VIDEO', exact: true }).click();
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '10', { timeout: 20000 });
  expect(calls).toEqual(Array(10).fill(1));
  const saved = await page.evaluate(() => JSON.parse(localStorage.getItem('muse-workstation-v1')!));
  expect(saved.settings.sharedAccountId).toBeUndefined();
  expect(saved.scenes.every((scene: any) => scene.accountId === undefined && scene.email === undefined)).toBe(true);
});

test('imports a 4K image batch from SRT, follows independent prompts, and converts the images to 1080p video requests', async ({ page }) => {
  await configureAdapter(page);
  const imageCalls: any[] = []; const videoCalls: any[] = [];
  await page.route('**/api/image', route => { imageCalls.push(route.request().postDataJSON()); return route.fulfill({ json: { base64: image, mimeType: 'image/png', metadata: { width: 3840, height: 2160 } } }); });
  await page.route('**/api/video', route => { videoCalls.push(route.request().postDataJSON()); return route.fulfill({ json: { base64: video, mimeType: 'video/mp4', metadata: { width: 640, height: 360, duration: 4 } } }); });
  await page.getByRole('button', { name: 'Tạo ảnh hàng loạt', exact: true }).click();
  await page.getByLabel('Độ nét ảnh', { exact: true }).selectOption('4k');
  await page.getByRole('checkbox', { name: 'Đồng nhất nhân vật', exact: true }).uncheck();
  await page.getByRole('button', { name: 'Nhập TXT / SRT', exact: true }).click();
  await page.getByLabel('Nội dung TXT / SRT').fill('1\n00:00:00,000 --> 00:00:04,000\nA person in a forest\n\n2\n00:00:04,000 --> 00:00:08,000\nA different person at sea');
  await page.getByRole('button', { name: 'Nạp & Chạy các cảnh', exact: true }).click();
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '2');
  expect(imageCalls.map(c => c.prompt)).toEqual(['A person in a forest', 'A different person at sea']);
  expect(imageCalls.every(c => c.resolution === '4k' && c.characterLock === false && c.image === undefined)).toBe(true);
  await expect(page.getByTestId('scene-1').locator('.video-metadata')).toHaveText('Muse trả về: 640×360');
  await expect(page.getByTestId('scene-1').locator('.quality-result')).toHaveText('Chưa đạt yêu cầu 4K');
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Tải cảnh 1', exact: true }).click();
  expect((await download).suggestedFilename()).toBe('image-01.png');
  await page.getByRole('button', { name: 'Chuyển bộ ảnh đã tạo sang video' }).click();
  await expect(page.getByRole('button', { name: 'Từ ảnh', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await page.getByLabel('Chất lượng', { exact: true }).selectOption('1080p');
  await page.getByRole('button', { name: 'TẠO 10 VIDEO', exact: true }).click();
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '2');
  expect(videoCalls).toHaveLength(2);
  expect(videoCalls.every(c => c.sourceMode === 'image' && c.image.imageBytes === image && c.characterLock === false && c.resolution === '1080p')).toBe(true);
  await page.getByRole('button', { name: 'Tạo ảnh hàng loạt', exact: true }).click();
  await expect(page.locator('.generated-image')).toHaveCount(2);
});

test('character lock attaches the portrait; disabling it and editing the prompt regenerates independently', async ({ page }) => {
  await configureAdapter(page);
  const calls: any[] = [];
  await page.route('**/api/image', route => { calls.push(route.request().postDataJSON()); return route.fulfill({ json: { base64: image, mimeType: 'image/png' } }); });
  await page.getByRole('button', { name: 'Tạo ảnh hàng loạt', exact: true }).click();
  const chooser = page.waitForEvent('filechooser');
  await page.getByRole('button', { name: 'Tải ảnh nhân vật chung' }).click();
  await (await chooser).setFiles({ name: 'portrait.png', mimeType: 'image/png', buffer: png });
  await expect(page.locator('.scene-image')).toHaveCount(10);
  await page.getByTestId('scene-1').getByRole('button', { name: 'Tạo cảnh này' }).click();
  await expect(page.getByTestId('scene-1').locator('.generated-image')).toBeVisible();
  expect(calls[0].image.imageBytes).toBe(png.toString('base64'));
  expect(calls[0].characterLock).toBe(true);
  await page.getByRole('checkbox', { name: 'Đồng nhất nhân vật', exact: true }).uncheck();
  await page.getByLabel('Kịch bản cảnh 1', { exact: true }).fill('A new independent character');
  await expect(page.getByTestId('scene-1').locator('.generated-image')).toHaveCount(0);
  await page.getByTestId('scene-1').getByRole('button', { name: 'Tạo cảnh này' }).click();
  await expect(page.getByTestId('scene-1').locator('.generated-image')).toBeVisible();
  expect(calls[1].image).toBeUndefined(); expect(calls[1].characterLock).toBe(false);
  expect(calls[1].prompt).toBe('A new independent character');
});

test('balance panel shows an observed zero and distinguishes an unreadable balance', async ({ page }) => {
  const account = { id: 1, state: 'ready', authenticated: true, active: true, checkedAt: null, balance: { valueText: '0', unit: 'token', label: 'Tokens remaining: 0', observedAt: new Date().toISOString(), source: 'muse-ui' } as any };
  await page.route('**/api/status', route => route.fulfill({ json: { museConfigured: true, transport: 'browser', accounts: [account], busy: false } }));
  await page.route('**/api/account/check', route => { account.balance = null; return route.fulfill({ json: { accounts: [account] } }); });
  await page.reload();
  await expect(page.getByTestId('account-balance')).toContainText('0 token');
  await page.getByRole('button', { name: 'Cập nhật số dư', exact: true }).click();
  await expect(page.getByTestId('account-balance')).toContainText('Chưa đọc được');
  await expect(page.getByTestId('account-balance')).not.toContainText('0 token');
});

test('large generated image is compressed only for video input while the original image is retained', async ({ page }) => {
  await configureAdapter(page);
  const largeImage = Buffer.concat([png, Buffer.alloc(9 * 1024 * 1024)]).toString('base64');
  await page.route('**/api/image', route => route.fulfill({ json: { base64: largeImage, mimeType: 'image/png' } }));
  let input: any;
  await page.route('**/api/video', route => { input = route.request().postDataJSON(); return route.fulfill({ json: { base64: video, mimeType: 'video/mp4' } }); });
  await page.getByRole('button', { name: 'Tạo ảnh hàng loạt', exact: true }).click();
  await page.getByTestId('scene-1').getByRole('button', { name: 'Tạo cảnh này' }).click();
  await expect(page.getByTestId('scene-1').locator('.generated-image')).toBeVisible();
  await page.getByTestId('scene-1').getByRole('button', { name: 'Dùng ảnh này tạo video', exact: true }).click();
  await page.getByTestId('scene-1').getByRole('button', { name: 'Tạo cảnh này' }).click();
  await expect(page.getByTestId('scene-1').locator('video')).toBeVisible();
  expect(input.image.mimeType).toBe('image/webp');
  expect(input.image.imageBytes.length).toBeLessThan(8 * 1024 * 1024 * 4 / 3);
  await expect(page.getByTestId('scene-1')).toContainText('Ảnh đầu vào đã nén dưới 8 MB; ảnh gốc được giữ.');
  await page.getByRole('button', { name: 'Tạo ảnh hàng loạt', exact: true }).click();
  await expect(page.getByTestId('scene-1').locator('.generated-image')).toBeVisible();
});

test('image-to-video batch only sends scenes that have a source frame', async ({ page }) => {
  await configureAdapter(page);
  const calls: number[] = [];
  await page.route('**/api/video', route => { calls.push(route.request().postDataJSON().accountId); return route.fulfill({ json: { base64: video, mimeType: 'video/mp4' } }); });
  await page.getByRole('button', { name: 'Từ ảnh', exact: true }).click();
  await expect(page.getByRole('button', { name: 'TẠO 10 VIDEO', exact: true })).toBeDisabled();
  const chooser = page.waitForEvent('filechooser');
  await page.getByTestId('scene-1').getByRole('button', { name: '+ Chọn ảnh nhân vật', exact: true }).click();
  await (await chooser).setFiles({ name: 'frame.png', mimeType: 'image/png', buffer: png });
  await expect(page.getByRole('button', { name: 'TẠO 10 VIDEO', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: 'TẠO 10 VIDEO', exact: true }).click();
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '1');
  expect(calls).toEqual([1]);
  await expect(page.locator('.scene-error')).toHaveCount(0);
});
