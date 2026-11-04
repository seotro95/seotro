import { chromium } from 'playwright-core';
import { existsSync } from 'node:fs';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { randomUUID } from 'node:crypto';

// Public UI selectors observed in community Muse clients, not an official SDK.
const EDITOR = '[data-hatch-composer-root] textarea, [data-hatch-composer-root] [contenteditable="true"]';
const MESSAGES = '[data-message-item]';
const STOP = '[data-testid="hatch-composer-stop-button"]';
const NOTICE = '[data-testid="assistant-response-error-notice"]';
const fail = (code, text, status = 502) => Object.assign(new Error(`${code}: ${text}`), { status });
const pause = (ms, signal) => new Promise((resolve, reject) => {
  if (signal?.aborted) return reject(signal.reason);
  const finish = () => { signal?.removeEventListener('abort', abort); resolve(); };
  const timer = setTimeout(finish, ms);
  const abort = () => { clearTimeout(timer); reject(signal.reason); };
  signal?.addEventListener('abort', abort, { once: true });
});

export class MuseBrowser {
  constructor({ profileRoot, serviceURL = 'https://muse.ai/', launchOptions, timeoutMs = 600000, pollMs = 500, quietMs = 1500 } = {}) {
    this.profileRoot = profileRoot;
    this.serviceURL = serviceURL;
    this.launchOptions = launchOptions;
    this.timeoutMs = timeoutMs;
    this.pollMs = pollMs;
    this.quietMs = quietMs;
    this.active = null;
    this.accounts = Array.from({ length: 10 }, (_, i) => ({ id: i + 1, state: existsSync(this.profile(i + 1)) ? 'saved' : 'disconnected', authenticated: false, checkedAt: null }));
  }
  profile(id) { return path.join(this.profileRoot, `slot-${String(id).padStart(2, '0')}`); }
  account(id) {
    if (!Number.isInteger(id) || id < 1 || id > 10) throw fail('ACCOUNT_INVALID', 'Slot tài khoản phải từ 1 đến 10.', 400);
    return this.accounts[id - 1];
  }
  snapshot() { return this.accounts.map(a => ({ ...a, active: this.active?.id === a.id })); }
  async close() {
    const active = this.active;
    this.active = null;
    if (active) {
      const account = this.account(active.id);
      account.state = account.authenticated ? 'session_saved' : 'saved';
      await active.context.close().catch(() => {});
    }
  }
  async open(id) {
    this.account(id);
    if (this.active?.id === id && !this.active.page.isClosed()) return this.active.page;
    if (this.active && !this.active.page.isClosed()) {
      const editor = this.active.page.locator(EDITOR).first();
      if ((await editor.inputValue().catch(() => '')).trim() || (await editor.innerText().catch(() => '')).trim()) throw fail('MUSE_DRAFT_EXISTS', 'Cửa sổ Muse hiện tại có bản nháp chưa gửi. Xử lý bản nháp trước khi chuyển slot tài khoản.', 409);
      if (await this.active.page.locator(STOP).first().isVisible().catch(() => false)) throw fail('MUSE_CHAT_BUSY', 'Muse vẫn đang xử lý trong cửa sổ hiện tại. Đợi hoàn tất trước khi chuyển tài khoản.', 409);
    }
    await this.close();
    const profile = this.profile(id);
    await mkdir(profile, { recursive: true, mode: 0o700 });
    let context;
    const proxyServer = process.env.HTTPS_PROXY || process.env.HTTP_PROXY;
    const defaults = { headless: false, viewport: null, timeout: 45000,
      ...(proxyServer ? { proxy: { server: proxyServer, bypass: 'localhost,127.0.0.1' } } : {}) };
    const choices = this.launchOptions ? [this.launchOptions] : process.env.MUSE_BROWSER_CHANNEL ? [{ channel: process.env.MUSE_BROWSER_CHANNEL }] : [{ channel: 'chrome' }, { channel: 'msedge' }];
    for (const choice of choices) {
      try { context = await chromium.launchPersistentContext(profile, { ...defaults, ...choice }); break; }
      catch (error) {
        if (/ProcessSingleton|profile.*in use|already.*running/i.test(error.message)) throw fail('MUSE_PROFILE_BUSY', 'Hồ sơ Muse này đang được một cửa sổ khác sử dụng. Đóng cửa sổ đó rồi kết nối lại.', 409);
      }
    }
    if (!context) throw fail('MUSE_BROWSER_UNAVAILABLE', 'Không mở được Chrome/Edge. Cài Google Chrome hoặc Microsoft Edge trên máy chạy tool; không cần đổi chính sách PowerShell.', 503);
    const page = context.pages()[0] || await context.newPage();
    this.active = { id, context, page };
    this.account(id).state = 'login_open';
    context.once('close', () => {
      if (this.active?.context === context) {
        this.account(id).state = this.account(id).authenticated ? 'session_saved' : 'saved';
        this.active = null;
      }
    });
    try { await page.goto(this.serviceURL, { waitUntil: 'domcontentloaded', timeout: 45000 }); }
    catch { throw fail('MUSE_CONNECTION_FAILED', 'Không mở được muse.ai trong cửa sổ đăng nhập. Kiểm tra mạng, proxy hoặc trang đăng nhập trên cửa sổ Muse.', 503); }
    return page;
  }
  async connect(id) {
    const page = await this.open(id);
    await page.bringToFront();
    await this.refreshActive();
    return this.snapshot();
  }
  async refreshActive() {
    const active = this.active;
    if (!active || active.page.isClosed()) return;
    const account = this.account(active.id);
    const serviceOrigin = new URL(this.serviceURL).origin;
    const servicePage = active.context.pages().find(p => { try { return new URL(p.url()).origin === serviceOrigin; } catch { return false; } });
    if (!servicePage) { account.authenticated = false; account.state = 'login_open'; return; }
    active.page = servicePage;
    // Only the owned browser uses its session. No cookie/token export or passwords.
    const authenticated = await active.page.evaluate(async () => {
      const abort = new AbortController();
      const timer = setTimeout(() => abort.abort(), 4000);
      try { const response = await fetch('/api/auth/check', { method: 'POST', signal: abort.signal }); return response.ok && (await response.json())?.ok === true; }
      catch { return false; }
      finally { clearTimeout(timer); }
    }).catch(() => false);
    const composerReady = await active.page.locator(EDITOR).first().isVisible().catch(() => false);
    // Do not replace another account's state if its window was switched mid-check.
    if (this.active !== active) return;
    account.authenticated = Boolean(authenticated && composerReady);
    account.state = account.authenticated ? 'ready' : 'login_open';
    account.checkedAt = new Date().toISOString();
  }
  async attach(page, image) {
    const input = page.locator('[data-hatch-composer-root] input[type="file"]').first();
    if (!await input.count()) throw fail('MUSE_ATTACHMENT_UNAVAILABLE', 'Không tìm thấy ô tải ảnh trong Muse. Chưa gửi prompt. Mở cửa sổ Muse kiểm tra giao diện hoặc bỏ ảnh tham chiếu trước khi thử lại.');
    await input.setInputFiles({ name: `reference.${image.mimeType === 'image/jpeg' ? 'jpg' : image.mimeType.split('/')[1]}`, mimeType: image.mimeType, buffer: Buffer.from(image.base64, 'base64') });
    try {
      await page.waitForFunction(() => Array.from(document.querySelectorAll('[data-hatch-composer-root] img')).some(img => img.complete && img.naturalWidth > 0), null, { timeout: 30000 });
    } catch { throw fail('MUSE_UPLOAD_NOT_READY', 'Ảnh chưa xuất hiện trong ô soạn Muse. Chưa gửi prompt; kiểm tra cửa sổ Muse rồi thử lại.'); }
  }
  async turn({ accountId, prompt, image, video, signal }) {
    await this.open(accountId);
    await this.refreshActive();
    if (!this.account(accountId).authenticated) throw fail('MUSE_LOGIN_REQUIRED', `Đăng nhập Muse cho slot ${accountId} trong cửa sổ Chrome/Edge, rồi bấm Kiểm tra phiên.`, 401);
    const page = this.active.page;
    signal.throwIfAborted();
    if (await page.locator(STOP).first().isVisible().catch(() => false)) throw fail('MUSE_CHAT_BUSY', 'Muse đang trả lời một yêu cầu khác. Đợi hoàn tất rồi thử lại.', 409);
      const editor = page.locator(EDITOR).first();
    if ((await editor.innerText().catch(() => '')).trim() || (await editor.inputValue().catch(() => '')).trim()) throw fail('MUSE_DRAFT_EXISTS', 'Ô soạn Muse đang có nội dung chưa gửi. Gửi hoặc xóa bản nháp đó trước; tool không ghi đè.', 409);
    if (await page.locator('[data-hatch-composer-root] img[src^="blob:"]').count()) throw fail('MUSE_DRAFT_EXISTS', 'Ô soạn Muse đang có ảnh chưa gửi. Xử lý bản nháp đó trước; tool không gửi kèm ảnh cũ.', 409);
    if (image) await this.attach(page, image);
    signal.throwIfAborted();
    const marker = `studio-request-${randomUUID()}`;
    const message = `${prompt}\n\n[Request marker: ${marker}. Do not include this marker in your reply.]`;
    await editor.fill(message);
    signal.throwIfAborted();
    await editor.press('Enter');
    const deadline = Date.now() + this.timeoutMs;
    let lastText = '';
    let stableSince = Date.now();
    try {
      while (Date.now() < deadline) {
        await pause(this.pollMs, signal);
        const result = await page.evaluate(({ messages, stop, notice, marker }) => {
          const visible = el => Boolean(el && el.getClientRects().length);
          const nodes = Array.from(document.querySelectorAll(messages));
          const anchor = nodes.findLastIndex(node => node.getAttribute('data-message-role') === 'user' && node.textContent.includes(marker));
          const replies = anchor < 0 ? [] : nodes.slice(anchor + 1).filter(node => node.getAttribute('data-message-role') === 'assistant');
          const videos = replies.flatMap(node => Array.from(node.querySelectorAll('video'))).filter(el => el.readyState >= 1 && el.currentSrc).map(el => ({ src: el.currentSrc, duration: el.duration, width: el.videoWidth, height: el.videoHeight }));
          const error = replies.flatMap(node => Array.from(node.querySelectorAll(notice))).find(visible);
          return { anchored: anchor >= 0, text: replies.map(node => node.innerText).join('\n\n').trim(), videos,
            streaming: visible(document.querySelector(stop)), error: error?.innerText || '' };
        }, { messages: MESSAGES, stop: STOP, notice: NOTICE, marker });
        if (result.error) throw fail('MUSE_GENERATION_ERROR', result.error);
        if (result.text !== lastText) { lastText = result.text; stableSince = Date.now(); }
        if (!video && result.anchored && result.text && !result.streaming && Date.now() - stableSince >= this.quietMs) return { text: result.text };
        if (video && result.videos.length && !result.streaming) {
          const media = result.videos[0];
          const base64 = await page.evaluate(async ({ src }) => {
            const url = new URL(src, location.href);
            if (!['https:', 'blob:', 'data:'].includes(url.protocol) && !(url.protocol === 'http:' && url.hostname === '127.0.0.1')) throw new Error('Unsupported video URL');
            const response = await fetch(url.href);
            if (!response.ok) throw new Error('Video download failed');
            const blob = await response.blob();
            if (!blob.size || blob.size > 100 * 1024 * 1024) throw new Error('Video must be between 1 byte and 100 MB');
            return await new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve({ base64: String(reader.result).split(',')[1], mimeType: blob.type }); reader.onerror = reject; reader.readAsDataURL(blob); });
          }, { src: media.src }).catch(() => { throw fail('MUSE_MEDIA_UNREADABLE', 'Muse đã hiển thị video nhưng tool chưa tải được dữ liệu. Mở cửa sổ Muse để tải trực tiếp; không thay bằng clip mẫu.'); });
          signal.throwIfAborted();
          return { ...base64, mimeType: base64.mimeType?.startsWith('video/') ? base64.mimeType : 'video/mp4', metadata: { duration: media.duration, width: media.width, height: media.height } };
        }
        if (video && result.text && !result.videos.length && !result.streaming && Date.now() - stableSince > 20000) throw fail('MUSE_NO_VIDEO', `Muse chưa trả video cho yêu cầu này. Phản hồi: ${result.text.slice(0, 1000)}`);
      }
      throw fail('MUSE_TIMEOUT', 'Hết thời gian chờ Muse. Kiểm tra cửa sổ Muse trước khi thử lại để tránh tạo trùng hoặc tính phí hai lần.', 504);
    } catch (error) {
      if (signal.aborted) { await page.locator(STOP).first().click({ timeout: 1000 }).catch(() => {}); throw signal.reason; }
      throw error;
    }
  }
  async generateVideo(data, signal) {
    const prompt = `Use your video-generation tool to create exactly one new video, not a link to an existing example. Requested model: ${data.modelDisplayName}. Requested duration: ${data.durationSeconds} seconds, aspect ratio: ${data.aspectRatio}, resolution: ${data.resolution}. If these capabilities are unavailable, explain that clearly. ${data.referenceImage ? 'Use the attached portrait as the character reference; preserve the character appearance.' : ''}\nScene:\n${data.prompt}`;
    return this.turn({ accountId: data.accountId, prompt, image: data.referenceImage, video: true, signal });
  }
  async generateText(data, signal) { return this.turn({ accountId: data.accountId, prompt: data.prompt, video: false, signal }); }
}
