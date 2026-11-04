import { chromium } from 'playwright-core';
import { existsSync } from 'node:fs';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { readMuseBalance } from './muse-balance.mjs';

// Public UI selectors observed in community Muse clients, not an official SDK.
// Muse retains a hidden prehydration textarea before its hydrated rich editor.
// Filter before first(): waiting on the first unfiltered match never reaches it.
const EDITOR = '[data-hatch-composer-root] textarea:not([data-hatch-composer-prehydration-input="true"]):visible, [data-hatch-composer-root] [contenteditable="true"]:visible, [data-hatch-composer-root] [contenteditable="plaintext-only"]:visible';
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
  constructor({ profileRoot, accountProfile, serviceURL = 'https://muse.ai/', launchOptions, sessionFactory, timeoutMs = 600000, pollMs = 500, quietMs = 1500, composerTimeoutMs = 45000 } = {}) {
    this.profileRoot = profileRoot;
    this.serviceURL = serviceURL;
    this.launchOptions = launchOptions;
    this.sessionFactory = sessionFactory;
    this.workers = new Map();
    this.opening = null;
    this.timeoutMs = timeoutMs;
    this.pollMs = pollMs;
    this.quietMs = quietMs;
    this.composerTimeoutMs = composerTimeoutMs;
    this.active = null;
    this.profilePath = accountProfile || path.join(this.profileRoot, 'slot-01');
    this.accounts = [{ id: 1, state: existsSync(this.profile(1)) ? 'saved' : 'disconnected', authenticated: false, checkedAt: null, balance: null }];
  }
  profile(id = 1) { this.requireSingleAccount(id); return this.profilePath; }
  requireSingleAccount(id) { if (id !== 1) throw fail('ACCOUNT_INVALID', 'Bản này chỉ sử dụng một tài khoản Muse duy nhất.', 400); }
  account(id) {
    this.requireSingleAccount(id);
    return this.accounts[id - 1];
  }
  snapshot() { return this.accounts.map(a => ({ ...a, active: this.active?.id === a.id })); }
  async close() {
    const active = this.active;
    this.active = null;
    if (active) {
      const account = this.account(active.id);
      account.state = account.authenticated ? 'session_saved' : 'saved';
      await (active.close ? active.close() : active.context.close()).catch(() => {});
    }
  }
  async open(id = 1) {
    this.account(id);
    if (this.active?.id === id && !this.active.page.isClosed()) return this.active.page;
    if (!this.opening) this.opening = this.openSession(id).finally(() => { this.opening = null; });
    return this.opening;
  }
  async openSession(id) {
    await this.close();
    if (this.sessionFactory) {
      const owned = await this.sessionFactory();
      this.active = { id, ...owned };
      this.account(id).state = 'login_open';
      await owned.page.goto(this.serviceURL, { waitUntil: 'domcontentloaded', timeout: 45000 });
      return owned.page;
    }
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
  async connect(id = 1, { show = true } = {}) {
    const page = await this.open(id);
    if (show) { if (this.active.showLogin) this.active.showLogin(); else await page.bringToFront(); }
    await this.refreshActive();
    return this.snapshot();
  }
  async refreshActive() {
    const active = this.active;
    if (!active || active.page.isClosed()) return;
    const account = this.account(active.id);
    // The login page remains separate from the ten worker conversations.
    if (new URL(active.page.url()).origin !== new URL(this.serviceURL).origin) {
      account.authenticated = false; account.state = 'login_open'; account.balance = null; return;
    }
    // Only the owned browser uses its session. No cookie/token export or passwords.
    const authenticated = await this.authenticated(active.page);
    const composerReady = await active.page.locator(EDITOR).first().isVisible().catch(() => false);
    if (this.active !== active) return;
    account.authenticated = Boolean(authenticated && composerReady);
    account.state = account.authenticated ? 'ready' : 'login_open';
    account.checkedAt = new Date().toISOString();
    account.balance = account.authenticated ? await readMuseBalance(active.page) : null;
  }
  async authenticated(page) {
    return page.evaluate(async () => {
      const abort = new AbortController();
      const timer = setTimeout(() => abort.abort(), 4000);
      try { const response = await fetch('/api/auth/check', { method: 'POST', signal: abort.signal }); return response.ok && (await response.json())?.ok === true; }
      catch { return false; }
      finally { clearTimeout(timer); }
    }).catch(() => false);
  }
  async waitForComposer(page) {
    try { await page.locator(EDITOR).first().waitFor({ state: 'visible', timeout: this.composerTimeoutMs }); }
    catch (error) {
      if (error.name !== 'TimeoutError') throw error;
      throw fail('MUSE_COMPOSER_NOT_READY', 'Muse chưa hiển thị ô soạn đã tải xong. Chưa gửi prompt. Mở tab Muse kiểm tra trang, rồi thử lại cảnh lỗi.', 504);
    }
  }
  async prepareConversation(page) {
    await this.waitForComposer(page);
    const users = page.locator(`${MESSAGES}[data-message-role="user"]`);
    if (!await users.count()) return;
    const newChat = page.getByRole('button', { name: /^(new chat|new conversation|cuộc trò chuyện mới|trò chuyện mới)$/i }).first();
    if (!await newChat.isVisible().catch(() => false)) throw fail('MUSE_NEW_CHAT_UNAVAILABLE', 'Không mở được cuộc trò chuyện riêng. Chưa gửi prompt; Muse cần hỗ trợ các cuộc trò chuyện độc lập để chạy đồng thời.');
    await newChat.click();
    await page.waitForFunction(selector => document.querySelectorAll(selector).length === 0, `${MESSAGES}[data-message-role="user"]`, { timeout: 15000 });
    await this.waitForComposer(page);
  }
  async attach(page, image) {
    const input = page.locator('[data-hatch-composer-root] input[type="file"]').first();
    if (!await input.count()) throw fail('MUSE_ATTACHMENT_UNAVAILABLE', 'Không tìm thấy ô tải ảnh trong Muse. Chưa gửi prompt. Mở cửa sổ Muse kiểm tra giao diện hoặc bỏ ảnh tham chiếu trước khi thử lại.');
    await input.setInputFiles({ name: `reference.${image.mimeType === 'image/jpeg' ? 'jpg' : image.mimeType.split('/')[1]}`, mimeType: image.mimeType, buffer: Buffer.from(image.base64, 'base64') });
    try {
      await page.waitForFunction(() => Array.from(document.querySelectorAll('[data-hatch-composer-root] img')).some(img => img.complete && img.naturalWidth > 0), null, { timeout: 30000 });
    } catch { throw fail('MUSE_UPLOAD_NOT_READY', 'Ảnh chưa xuất hiện trong ô soạn Muse. Chưa gửi prompt; kiểm tra cửa sổ Muse rồi thử lại.'); }
  }
  async turn({ accountId, prompt, image, video, output = video ? 'video' : 'text', signal }) {
    this.requireSingleAccount(accountId);
    if (this.workers.size >= 10) throw fail('MUSE_CONCURRENCY_LIMIT', 'Đã có 10 luồng đang chạy trên tài khoản Muse.', 429);
    const key = randomUUID();
    this.workers.set(key, null);
    let page; let owned; let sending = false;
    const cancelled = () => { if (page && !sending) void (owned?.destroyWorkerPage ? owned.destroyWorkerPage(page) : page.close()).catch(() => {}); };
    signal.addEventListener('abort', cancelled, { once: true });
    try {
      signal.throwIfAborted();
      await this.open(accountId);
      owned = this.active;
      await this.refreshActive();
      if (!this.account(accountId).authenticated) throw fail('MUSE_LOGIN_REQUIRED', 'Đăng nhập tài khoản Muse trong tool, rồi bấm Kiểm tra phiên.', 401);
      signal.throwIfAborted();
      page = owned.createWorkerPage ? await owned.createWorkerPage() : await owned.context.newPage();
      this.workers.set(key, page);
      signal.throwIfAborted();
      await page.goto(this.serviceURL, { waitUntil: 'domcontentloaded', timeout: 45000 });
      if (!await this.authenticated(page)) {
        this.account(accountId).authenticated = false;
        throw fail('MUSE_LOGIN_REQUIRED', 'Phiên Muse đã hết hạn. Đăng nhập lại tài khoản trong tool.', 401);
      }
      await this.prepareConversation(page);
      signal.throwIfAborted();
      if (await page.locator(STOP).first().isVisible().catch(() => false)) throw fail('MUSE_CHAT_BUSY', 'Cuộc trò chuyện này đang xử lý yêu cầu khác. Chưa gửi prompt.', 409);
      sending = true;
      return await this.sendTurn({ page, prompt, image, output, signal });
    } finally {
      signal.removeEventListener('abort', cancelled);
      if (page) await (owned?.destroyWorkerPage ? owned.destroyWorkerPage(page) : page.close()).catch(() => {});
      this.workers.delete(key);
    }
  }
  async sendTurn({ page, prompt, image, output, signal }) {
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
          const images = replies.flatMap(node => Array.from(node.querySelectorAll('img'))).filter(el => !el.closest('video') && el.complete && el.naturalWidth >= 128 && el.naturalHeight >= 128).map(el => ({ src: el.currentSrc || el.src, width: el.naturalWidth, height: el.naturalHeight }));
          const error = replies.flatMap(node => Array.from(node.querySelectorAll(notice))).find(visible);
          return { anchored: anchor >= 0, text: replies.map(node => node.innerText).join('\n\n').trim(), videos, images,
            streaming: visible(document.querySelector(stop)), error: error?.innerText || '' };
        }, { messages: MESSAGES, stop: STOP, notice: NOTICE, marker });
        if (result.error) throw fail('MUSE_GENERATION_ERROR', result.error);
        if (result.text !== lastText) { lastText = result.text; stableSince = Date.now(); }
        if (output === 'text' && result.anchored && result.text && !result.streaming && Date.now() - stableSince >= this.quietMs) return { text: result.text };
        const media = output === 'video' ? result.videos[0] : output === 'image' ? result.images[0] : null;
        if (media && !result.streaming) {
          const base64 = await page.evaluate(async ({ src }) => {
            const url = new URL(src, location.href);
            if (!['https:', 'blob:', 'data:'].includes(url.protocol) && !(url.protocol === 'http:' && url.hostname === '127.0.0.1')) throw new Error('Unsupported media URL');
            const response = await fetch(url.href);
            if (!response.ok) throw new Error('Video download failed');
            const blob = await response.blob();
            if (!blob.size || blob.size > 100 * 1024 * 1024) throw new Error('Video must be between 1 byte and 100 MB');
            return await new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve({ base64: String(reader.result).split(',')[1], mimeType: blob.type }); reader.onerror = reject; reader.readAsDataURL(blob); });
          }, { src: media.src }).catch(() => { throw fail('MUSE_MEDIA_UNREADABLE', 'Muse đã hiển thị kết quả nhưng tool chưa tải được dữ liệu. Mở lịch sử trò chuyện trong tab Muse để tải trực tiếp.'); });
          signal.throwIfAborted();
          return { ...base64, mimeType: base64.mimeType?.startsWith(`${output}/`) ? base64.mimeType : output === 'image' ? 'image/png' : 'video/mp4', metadata: { ...(output === 'video' ? { duration: media.duration } : {}), width: media.width, height: media.height } };
        }
        if (output !== 'text' && result.text && !media && !result.streaming && Date.now() - stableSince > 20000) throw fail(output === 'image' ? 'MUSE_NO_IMAGE' : 'MUSE_NO_VIDEO', `Muse chưa trả ${output === 'image' ? 'ảnh' : 'video'} cho yêu cầu này. Phản hồi: ${result.text.slice(0, 1000)}`);
      }
      throw fail('MUSE_TIMEOUT', 'Hết thời gian chờ Muse. Kiểm tra cửa sổ Muse trước khi thử lại để tránh tạo trùng hoặc tính phí hai lần.', 504);
    } catch (error) {
      if (signal.aborted) {
        // A hidden worker still has a live DOM. Dispatch Stop there and give its
        // request time to finish before disposing the view, which aborts fetches.
        await page.locator(STOP).first().evaluate(button => button.click(), undefined, { timeout: 1000 }).catch(() => {});
        await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
        throw signal.reason;
      }
      throw error;
    }
  }
  async generateVideo(data, signal) {
    const referenceInstruction = data.sourceMode === 'image' ? 'Animate the attached image as the starting frame.' : data.referenceImage ? 'Use the attached image as a character reference, not as an unrelated example.' : 'Create the video from the text prompt.';
    const prompt = `Use your video-generation tool to create exactly one new video, not a link to an existing example. Requested model: ${data.modelDisplayName}. Requested duration: ${data.durationSeconds} seconds, aspect ratio: ${data.aspectRatio}, resolution: ${data.resolution}. If these capabilities are unavailable, explain that clearly. ${referenceInstruction} ${data.characterLock !== false ? 'Preserve the referenced character identity and appearance across scenes.' : 'Follow this scene prompt independently; character consistency is not requested.'}\nScene:\n${data.prompt}`;
    return this.turn({ accountId: data.accountId, prompt, image: data.referenceImage, video: true, signal });
  }
  async generateImage(data, signal) {
    const longEdge = data.resolution === '4k' ? 3840 : 2560;
    const dimensions = data.aspectRatio === '9:16' ? `${Math.round(longEdge * 9 / 16)}x${longEdge}` : `${longEdge}x${Math.round(longEdge * 9 / 16)}`;
    const useReference = data.characterLock !== false && data.referenceImage;
    const prompt = `Use your image-generation tool to create exactly one new image for this scene. Requested native output: ${data.resolution.toUpperCase()} (${dimensions} pixels), aspect ratio ${data.aspectRatio}. Return the generated image, not a stock image or an old response. Do not claim a higher resolution than the image actually has. ${useReference ? 'Use the attached portrait as a character reference; preserve identity, face and appearance consistently.' : data.characterLock !== false ? 'Follow the character description in this prompt. No portrait is attached; cross-scene identity is not guaranteed without a reference.' : 'Follow this prompt independently. Do not reuse characters or appearance from earlier scenes unless the prompt explicitly requests them.'}\nScene:\n${data.prompt}`;
    return this.turn({ accountId: data.accountId, prompt, image: useReference || undefined, output: 'image', signal });
  }
  async generateText(data, signal) { return this.turn({ accountId: data.accountId, prompt: data.prompt, video: false, signal }); }
}
