import { chromium } from 'playwright-core';
import { existsSync } from 'node:fs';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { readMuseBalance } from './muse-balance.mjs';

// Public UI selectors observed in community Muse clients, not an official SDK.
// Muse retains a prehydration textarea before its hydrated rich editor. It may
// need focus/click to initialize that editor, but must never receive a prompt.
const EDITOR = '[data-hatch-composer-root] textarea:not([data-hatch-composer-prehydration-input="true"]):not([readonly]):not([disabled]):visible, [data-hatch-composer-root] [contenteditable="true"]:visible, [data-hatch-composer-root] [contenteditable="plaintext-only"]:visible';
const PREHYDRATION = '[data-hatch-composer-root] textarea[data-hatch-composer-prehydration-input="true"]:not([readonly]):not([disabled]):visible';
const FIELD = 'textarea:not([data-hatch-composer-prehydration-input="true"]):not([readonly]):not([disabled]), [contenteditable="true"], [contenteditable="plaintext-only"]';
const NAMED_EDITOR = ['Message', 'Message Muse', 'Tin nhắn', 'Nhập tin nhắn'].flatMap(label => FIELD.split(', ').flatMap(field =>
  [`${field}[aria-label="${label}" i]:visible`, `${field}[placeholder="${label}" i]:visible`]
)).concat('[data-lexical-editor="true"][contenteditable="true"]:visible').map(selector => `${selector}:not([data-message-item] *)`).join(', ');
const NEW_CHAT = /^(new chat|new conversation|cuộc trò chuyện mới|trò chuyện mới|bắt đầu trò chuyện)$/i;
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
    this.accounts = [{ id: 1, state: existsSync(this.profile(1)) ? 'saved' : 'disconnected', authenticated: false, sessionAuthenticated: false, composerReady: false, connectionMessage: '', checkedAt: null, balance: null }];
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
    // The login page may be a dashboard or a stale OAuth landing page. Its
    // editor is not a prerequisite: every render opens and checks its own page.
    return this.snapshot();
  }
  async refreshActive() {
    const active = this.active;
    if (!active || active.page.isClosed()) return;
    const account = this.account(active.id);
    account.checkedAt = new Date().toISOString();
    // The login page remains separate from the ten worker conversations.
    if (new URL(active.page.url()).origin !== new URL(this.serviceURL).origin) {
      Object.assign(account, { authenticated: false, sessionAuthenticated: false, composerReady: false, state: 'login_open', balance: null, connectionMessage: 'Hoàn tất đăng nhập để tab xác thực quay về Muse, rồi bấm Kiểm tra phiên.' }); return;
    }
    // Only the owned browser uses its session. No cookie/token export or passwords.
    const probe = await this.inspectAuthentication(active.page);
    const composerReady = Boolean(await this.findComposer(active.page).catch(() => null));
    if (this.active !== active) return;
    account.sessionAuthenticated = probe.authenticated;
    account.composerReady = composerReady;
    account.authenticated = probe.authenticated;
    account.state = probe.authenticated ? 'ready' : probe.state;
    account.connectionMessage = probe.authenticated ? 'Phiên Muse đã được xác minh. Tool mở ô soạn riêng khi bạn bấm tạo từng cảnh hoặc cả bộ.' : probe.message;
    account.balance = account.authenticated ? await readMuseBalance(active.page) : null;
  }
  async authenticated(page) {
    return (await this.inspectAuthentication(page)).authenticated;
  }
  async inspectAuthentication(page) {
    return page.evaluate(async () => {
      const abort = new AbortController();
      const timer = setTimeout(() => abort.abort(), 4000);
      try {
        const response = await fetch('/api/auth/check', { method: 'POST', signal: abort.signal });
        const data = await response.json().catch(() => null);
        if (response.ok && data?.ok === true) return { authenticated: true, state: 'ready', message: '' };
        if (response.status === 401 || (response.ok && data?.ok === false)) return { authenticated: false, state: 'login_open', message: 'Chưa xác minh được phiên đăng nhập. Hoàn tất đăng nhập trong tab Muse rồi quay về Studio.' };
        return { authenticated: false, state: 'check_failed', message: `Không xác minh được phiên Muse (HTTP ${response.status}). Kiểm tra tab Muse rồi thử Kiểm tra phiên lại.` };
      }
      catch { return { authenticated: false, state: 'check_failed', message: 'Không đọc được trạng thái phiên từ Muse. Kiểm tra kết nối mạng và tab Muse rồi thử Kiểm tra phiên lại.' }; }
      finally { clearTimeout(timer); }
    }).catch(() => ({ authenticated: false, state: 'check_failed', message: 'Chưa đọc được trang Muse để xác minh phiên. Mở tab Muse rồi kiểm tra lại.' }));
  }
  async findComposer(page) {
    const frames = await this.composerFrames(page);
    for (const selector of [EDITOR, NAMED_EDITOR]) {
      const matches = [];
      for (const frame of frames) {
        const candidates = frame.locator(selector);
        for (let index = 0, count = await candidates.count(); index < count; index++) matches.push(candidates.nth(index));
      }
      if (matches.length === 1) return matches[0];
      if (matches.length > 1) throw fail('MUSE_COMPOSER_AMBIGUOUS', 'Có nhiều ô nhập phù hợp trong cuộc trò chuyện Muse. Chưa gửi prompt để tránh nhập nhầm ô.');
    }
    return null;
  }
  async composerFrames(page) {
    if (!page.frames) return [page];
    const frames = [page.mainFrame()];
    for (const frame of page.frames()) {
      if (frame === page.mainFrame() || new URL(frame.url(), this.serviceURL).origin !== new URL(this.serviceURL).origin) continue;
      const element = await frame.frameElement().catch(() => null);
      try { if (await element?.isVisible()) frames.push(frame); }
      finally { await element?.dispose(); }
    }
    return frames;
  }
  async activateComposerPlaceholder(page, timeout) {
    const matches = [];
    for (const frame of await this.composerFrames(page)) {
      const candidates = frame.locator(PREHYDRATION);
      for (let index = 0, count = await candidates.count(); index < count; index++) matches.push(candidates.nth(index));
    }
    if (matches.length > 1) throw fail('MUSE_COMPOSER_AMBIGUOUS', 'Có nhiều ô Message ban đầu trong trang Muse. Chưa kích hoạt hoặc gửi prompt để tránh chọn nhầm ô.');
    if (!matches.length) return false;
    const placeholder = matches[0];
    if ((await placeholder.inputValue()).trim()) throw fail('MUSE_DRAFT_EXISTS', 'Ô Message ban đầu đang có bản nháp. Tool giữ nguyên nội dung và chưa gửi prompt.', 409);
    try {
      // A background Electron view can receive a click without focusing its
      // iframe input. DOM focus initializes focus-driven editors there too.
      await placeholder.focus({ timeout: Math.min(1500, timeout) });
      if (await placeholder.isVisible()) await placeholder.click({ timeout: Math.min(1500, timeout) });
    }
    catch (error) { if (error.name !== 'TimeoutError') throw error; }
    // Focus/click only. The hydrated editor must still pass findComposer().
    return true;
  }
  async newChatControl(page) {
    for (const frame of await this.composerFrames(page)) {
      const entry = frame.getByRole('button', { name: NEW_CHAT }).or(frame.getByRole('link', { name: NEW_CHAT })).filter({ visible: true }).first();
      if (await entry.count()) return entry;
    }
    return null;
  }
  workerURL() {
    // Use the user's verified app route, rather than sending every worker back
    // to a marketing/landing page. OAuth query parameters are never copied.
    const current = new URL(this.active.page.url());
    const service = new URL(this.serviceURL);
    return current.origin === service.origin && !/\/(?:auth|oauth|login|signin|callback)(?:\/|$)/i.test(current.pathname)
      ? new URL(current.pathname, service.origin).href : this.serviceURL;
  }
  async composerDiagnostics(page) {
    const frames = page.frames ? page.frames() : [page];
    const known = new Set(['app', 'chat', 'chats', 'new', 'home', 'workspace', 'studio', 'login', 'auth', 'signin', 'callback']);
    return Promise.all(frames.slice(0, 8).map(async frame => {
      const url = new URL(frame.url(), this.serviceURL);
      const route = url.pathname.split('/').map(part => !part || known.has(part.toLowerCase()) ? part : '[ẩn]').join('/');
      const metrics = await frame.evaluate(() => {
        const visible = el => el.getClientRects().length > 0 && getComputedStyle(el).visibility !== 'hidden';
        return { ready: document.readyState, visibility: document.visibilityState, viewport: [innerWidth, innerHeight],
          composerRoots: document.querySelectorAll('[data-hatch-composer-root]').length,
          prehydration: document.querySelectorAll('[data-hatch-composer-prehydration-input="true"]').length,
          visiblePrehydration: [...document.querySelectorAll('[data-hatch-composer-prehydration-input="true"]')].filter(visible).length,
          visibleEditors: [...document.querySelectorAll('textarea, [contenteditable="true"], [contenteditable="plaintext-only"]')].filter(visible).length };
      }).catch(() => ({ ready: 'unavailable' }));
      return { origin: url.origin, route, ...metrics };
    }));
  }
  async waitForComposer(page, { openConversation = false } = {}) {
    const deadline = Date.now() + this.composerTimeoutMs;
    let opened = false;
    let activated = false;
    do {
      const editor = await this.findComposer(page);
      if (editor) return editor;
      if (!activated) activated = await this.activateComposerPlaceholder(page, Math.max(1, deadline - Date.now()));
      if (openConversation && !opened && !activated) {
        const entry = await this.newChatControl(page);
        if (entry) { await entry.click(); opened = true; }
      }
      await pause(Math.min(100, Math.max(1, deadline - Date.now())));
    } while (Date.now() < deadline);
    const details = await this.composerDiagnostics(page);
    throw fail('MUSE_COMPOSER_NOT_READY', `Chưa mở được ô nhập trong cuộc trò chuyện Muse của cảnh này. Chưa gửi prompt. Đã thử kích hoạt ô Message ban đầu: ${activated ? 'có' : 'không'}. Chẩn đoán trang luồng (không chứa nội dung chat): ${JSON.stringify(details)}`, 504);
  }
  async prepareConversation(page) {
    const editor = await this.waitForComposer(page, { openConversation: true });
    const handle = await editor.elementHandle();
    let frame;
    try { frame = await handle.ownerFrame(); }
    finally { await handle.dispose(); }
    const users = frame.locator(`${MESSAGES}[data-message-role="user"]`);
    if (!await users.count()) return frame;
    const newChat = await this.newChatControl(frame);
    if (!newChat) throw fail('MUSE_NEW_CHAT_UNAVAILABLE', 'Không mở được cuộc trò chuyện riêng. Chưa gửi prompt; Muse cần hỗ trợ các cuộc trò chuyện độc lập để chạy đồng thời.');
    await newChat.click();
    await frame.waitForFunction(selector => document.querySelectorAll(selector).length === 0, `${MESSAGES}[data-message-role="user"]`, { timeout: 15000 });
    await this.waitForComposer(frame);
    return frame;
  }
  async attach(page, image) {
    const editor = await this.waitForComposer(page);
    const hatch = editor.locator('xpath=ancestor::*[@data-hatch-composer-root][1]');
    const form = editor.locator('xpath=ancestor::form[1]');
    const area = await hatch.count() ? hatch : form;
    const input = area.locator('input[type="file"]').first();
    if (!await input.count()) throw fail('MUSE_ATTACHMENT_UNAVAILABLE', 'Không tìm thấy ô tải ảnh trong Muse. Chưa gửi prompt. Mở cửa sổ Muse kiểm tra giao diện hoặc bỏ ảnh tham chiếu trước khi thử lại.');
    await input.setInputFiles({ name: `reference.${image.mimeType === 'image/jpeg' ? 'jpg' : image.mimeType.split('/')[1]}`, mimeType: image.mimeType, buffer: Buffer.from(image.base64, 'base64') });
    const areaHandle = await area.elementHandle();
    try {
      await page.waitForFunction(root => root && Array.from(root.querySelectorAll('img')).some(img => !img.closest('[data-message-item]') && img.complete && img.naturalWidth > 0), areaHandle, { timeout: 30000 });
    } catch { throw fail('MUSE_UPLOAD_NOT_READY', 'Ảnh chưa xuất hiện trong ô soạn Muse. Chưa gửi prompt; kiểm tra cửa sổ Muse rồi thử lại.'); }
    finally { await areaHandle?.dispose(); }
  }
  async turn({ accountId, prompt, image, video, output = video ? 'video' : 'text', signal, checkOnly = false }) {
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
      if (!this.account(accountId).authenticated) {
        const account = this.account(accountId);
        const code = account.state === 'check_failed' ? 'MUSE_SESSION_CHECK_FAILED' : 'MUSE_LOGIN_REQUIRED';
        throw fail(code, account.connectionMessage || 'Đăng nhập tài khoản Muse trong tool, rồi bấm Kiểm tra phiên.', code === 'MUSE_LOGIN_REQUIRED' ? 401 : 503);
      }
      signal.throwIfAborted();
      page = owned.createWorkerPage ? await owned.createWorkerPage() : await owned.context.newPage();
      this.workers.set(key, page);
      signal.throwIfAborted();
      await page.goto(this.workerURL(), { waitUntil: 'domcontentloaded', timeout: 45000 });
      if (new URL(page.url()).origin !== new URL(this.serviceURL).origin) throw fail('MUSE_WORKSPACE_ORIGIN', 'Trang luồng chuyển sang miền khác Muse. Chưa nhập hoặc gửi prompt. Hoàn tất đăng nhập trong tab Muse rồi kiểm tra lại phiên.', 409);
      const workerProbe = await this.inspectAuthentication(page);
      if (!workerProbe.authenticated) {
        Object.assign(this.account(accountId), { authenticated: false, sessionAuthenticated: false, composerReady: false, state: workerProbe.state, connectionMessage: workerProbe.message });
        throw fail(workerProbe.state === 'check_failed' ? 'MUSE_SESSION_CHECK_FAILED' : 'MUSE_LOGIN_REQUIRED', workerProbe.message, workerProbe.state === 'check_failed' ? 503 : 401);
      }
      const conversation = await this.prepareConversation(page);
      signal.throwIfAborted();
      if (await conversation.locator(STOP).first().isVisible().catch(() => false)) throw fail('MUSE_CHAT_BUSY', 'Cuộc trò chuyện này đang xử lý yêu cầu khác. Chưa gửi prompt.', 409);
      if (checkOnly) return { ready: true, message: 'Đã mở được ô Message trong trang luồng riêng. Chưa gửi prompt hoặc yêu cầu tạo nội dung.', details: await this.composerDiagnostics(page) };
      return await this.sendTurn({ page: conversation, prompt, image, output, signal, onSubmit: () => { sending = true; } });
    } finally {
      signal.removeEventListener('abort', cancelled);
      if (page) await (owned?.destroyWorkerPage ? owned.destroyWorkerPage(page) : page.close()).catch(() => {});
      this.workers.delete(key);
    }
  }
  async checkComposer(signal) { return this.turn({ accountId: 1, checkOnly: true, signal }); }
  async sendTurn({ page, prompt, image, output, signal, onSubmit }) {
    const editor = await this.waitForComposer(page);
    if ((await editor.innerText().catch(() => '')).trim() || (await editor.inputValue().catch(() => '')).trim()) throw fail('MUSE_DRAFT_EXISTS', 'Ô soạn Muse đang có nội dung chưa gửi. Gửi hoặc xóa bản nháp đó trước; tool không ghi đè.', 409);
    if (await editor.locator('xpath=ancestor::*[@data-hatch-composer-root or self::form][1]').locator('img[src^="blob:"]:not([data-message-item] *)').count()) throw fail('MUSE_DRAFT_EXISTS', 'Ô soạn Muse đang có ảnh chưa gửi. Xử lý bản nháp đó trước; tool không gửi kèm ảnh cũ.', 409);
    if (image) await this.attach(page, image);
    signal.throwIfAborted();
    const marker = `studio-request-${randomUUID()}`;
    const message = `${prompt}\n\n[Request marker: ${marker}. Do not include this marker in your reply.]`;
    await editor.fill(message);
    signal.throwIfAborted();
    onSubmit();
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
