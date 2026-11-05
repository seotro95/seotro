import { chromium } from 'playwright-core';
import { existsSync } from 'node:fs';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { readMuseBalance } from './muse-balance.mjs';

// Public UI selectors observed in community Muse clients, not an official SDK.
// Muse retains a prehydration textarea before its hydrated rich editor. It may
// need focus or the first keystroke to initialize a rich editor. Some clients
// retain that attribute on a working textarea, so it is a scoped fallback.
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
const OTP_INPUT = [
  'input[autocomplete~="one-time-code" i]', 'input[name="otp" i]',
  'input[name="verificationCode" i]', 'input[name="verification_code" i]',
  'input[aria-label="Verification code" i]', 'input[aria-label="Mã xác nhận" i]',
  'input[aria-label="Mã xác minh" i]',
].map(selector => `${selector}:visible:not([data-message-item] *)`).join(', ');
// Chromium's rich editor can expose extra blank lines via innerText after fill.
// Compare normalized layout whitespace; the original prompt is still entered.
const comparableText = text => text.replace(/\r\n?/g, '\n').replace(/\u00a0/g, ' ').replace(/\n+/g, '\n').trim();
const fail = (code, text, status = 502) => Object.assign(new Error(`${code}: ${text}`), { status });
const pause = (ms, signal) => new Promise((resolve, reject) => {
  if (signal?.aborted) return reject(signal.reason);
  const finish = () => { signal?.removeEventListener('abort', abort); resolve(); };
  const timer = setTimeout(finish, ms);
  const abort = () => { clearTimeout(timer); reject(signal.reason); };
  signal?.addEventListener('abort', abort, { once: true });
});

export class MuseBrowser {
  constructor({ profileRoot, accountProfile, serviceURL = 'https://muse.ai/', launchOptions, sessionFactory, timeoutMs = 600000, pollMs = 500, quietMs = 1500, composerTimeoutMs = 45000, submitTimeoutMs = 15000, maxConcurrency = 1 } = {}) {
    this.profileRoot = profileRoot;
    this.serviceURL = serviceURL;
    this.launchOptions = launchOptions;
    this.sessionFactory = sessionFactory;
    this.workers = new Map();
    this.workerStages = new Map();
    this.opening = null;
    this.timeoutMs = timeoutMs;
    this.pollMs = pollMs;
    this.quietMs = quietMs;
    this.composerTimeoutMs = composerTimeoutMs;
    this.submitTimeoutMs = submitTimeoutMs;
    this.maxConcurrency = Math.max(1, Math.min(10, maxConcurrency));
    this.reserved = 0;
    this.executing = 0;
    this.queue = [];
    this.inFlightMarkers = new Set();
    this.unsafeMarkers = new Set();
    this.imageBatches = new Map();
    this.parallelRoutes = [];
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
  progress() { return [...this.workerStages.values()].map(stage => ({ ...stage })); }
  async close() {
    const active = this.active;
    this.active = null;
    if (active) {
      if (this.parallelRoutes.length) this.maxConcurrency = 1;
      this.parallelRoutes = [];
      const account = this.account(active.id);
      account.state = account.authenticated ? 'session_saved' : 'saved';
      await (active.close ? active.close() : active.context.close()).catch(() => {});
    }
  }
  async open(id = 1, { show = false } = {}) {
    this.account(id);
    if (this.active?.id === id && !this.active.page.isClosed()) return this.active.page;
    if (!this.opening) this.opening = this.openSession(id, { show }).finally(() => { this.opening = null; });
    return this.opening;
  }
  async openSession(id, { show = false } = {}) {
    await this.close();
    if (this.sessionFactory) {
      const owned = await this.sessionFactory();
      this.active = { id, ...owned };
      this.account(id).state = 'login_open';
      if (show) owned.showLogin?.();
      try { await owned.page.goto(this.serviceURL, { waitUntil: 'domcontentloaded', timeout: 45000 }); }
      catch { throw fail('MUSE_CONNECTION_FAILED', 'Không tải được trang Muse. Kiểm tra Internet rồi bấm Tải lại Muse; phiên cũ vẫn được giữ.', 503); }
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
    const page = await this.open(id, { show });
    if (show) { if (this.active.showLogin) this.active.showLogin(); else await page.bringToFront(); }
    await this.refreshActive();
    // The login page may be a dashboard or a stale OAuth landing page. Its
    // editor is not a prerequisite: every render opens and checks its own page.
    return this.snapshot();
  }
  async reopenLogin() {
    const page = await this.open(1, { show: true });
    this.active.showLogin?.();
    try { await page.goto(this.serviceURL, { waitUntil: 'domcontentloaded', timeout: 45000 }); }
    catch { throw fail('MUSE_CONNECTION_FAILED', 'Không tải được trang Muse. Kiểm tra Internet rồi bấm Tải lại Muse; không xóa phiên hoặc dữ liệu đã lưu.', 503); }
    await this.refreshActive();
  }
  async openEmailLink(raw) {
    let target;
    try {
      if (typeof raw !== 'string' || raw.length > 8192) throw new Error();
      target = new URL(raw.trim());
      const service = new URL(this.serviceURL);
      const sameOrigin = target.origin === service.origin;
      const museSubdomain = service.protocol === 'https:' && target.protocol === 'https:' && target.hostname.endsWith(`.${service.hostname}`);
      if (target.username || target.password || !(sameOrigin || museSubdomain)) throw new Error();
    } catch { throw fail('MUSE_EMAIL_LINK_INVALID', 'Chỉ mở liên kết Muse.ai hoặc miền phụ của Muse.ai. Hãy sao chép nguyên địa chỉ liên kết đăng nhập từ email.', 400); }
    const page = await this.open(1, { show: true });
    this.active.showLogin?.();
    try {
      const response = await page.goto(target.href, { waitUntil: 'domcontentloaded', timeout: 45000 });
      if (response && response.status() >= 400) throw new Error('Email callback refused');
    }
    catch { throw fail('MUSE_EMAIL_LINK_FAILED', 'Chưa mở được liên kết trong phiên Muse. Kiểm tra Internet; nếu liên kết đã dùng hoặc hết hạn, yêu cầu email mới.', 503); }
    await this.refreshActive();
  }
  async pendingCode(page) {
    const frames = page.frames ? page.frames() : [page];
    for (const frame of frames.slice(0, 12)) {
      try {
        if (page.mainFrame && frame !== page.mainFrame()) {
          const element = await frame.frameElement();
          try { if (!await element.isVisible()) continue; } finally { await element.dispose(); }
        }
        if (await frame.locator(OTP_INPUT).count()) return true;
      } catch { /* A navigating frame will be inspected on the next check. */ }
    }
    return false;
  }
  async refreshActive({ background = false } = {}) {
    const active = this.active;
    if (!active || active.page.isClosed()) return;
    // The website owns the challenge. Background status polling must not send
    // anonymous auth POSTs while the user is requesting/entering a code.
    if (background && active.isLoginVisible?.()) return;
    const account = this.account(active.id);
    // The login page remains separate from the ten worker conversations.
    if (new URL(active.page.url()).origin !== new URL(this.serviceURL).origin) {
      Object.assign(account, { authenticated: false, sessionAuthenticated: false, composerReady: false, state: 'login_open', balance: null, connectionMessage: 'Hoàn tất đăng nhập để tab xác thực quay về Muse, rồi bấm Kiểm tra phiên.' }); return;
    }
    if (await this.pendingCode(active.page)) {
      if (this.active !== active) return;
      Object.assign(account, { authenticated: false, sessionAuthenticated: false, composerReady: false, state: 'awaiting_code', balance: null,
        connectionMessage: 'Đang chờ xác nhận mã trên trang Muse. Tool giữ nguyên phiên và tạm ngừng kiểm tra ngầm. Nhập mã mới nhất, xác nhận xong rồi quay về Studio.' });
      return;
    }
    account.checkedAt = new Date().toISOString();
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
    const placeholder = await this.initialComposer(page);
    if (!placeholder) return false;
    if ((await placeholder.inputValue()).trim()) throw fail('MUSE_DRAFT_EXISTS', 'Ô Message ban đầu đang có bản nháp. Tool giữ nguyên nội dung và chưa gửi prompt.', 409);
    try {
      await placeholder.focus({ timeout: Math.min(1500, timeout) });
      if (await placeholder.isVisible() && !await placeholder.evaluate(el => el === el.ownerDocument.activeElement)) await placeholder.click({ timeout: Math.min(1500, timeout) });
    } catch (error) { if (error.name !== 'TimeoutError') throw error; }
    return true;
  }
  async initialComposer(page) {
    const matches = [];
    for (const frame of await this.composerFrames(page)) {
      const candidates = frame.locator(PREHYDRATION);
      for (let index = 0, count = await candidates.count(); index < count; index++) matches.push(candidates.nth(index));
    }
    if (matches.length > 1) throw fail('MUSE_COMPOSER_AMBIGUOUS', 'Có nhiều ô Message ban đầu trong trang Muse. Chưa kích hoạt hoặc gửi prompt để tránh chọn nhầm ô.');
    return matches[0] || null;
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
  conversationURL(page) {
    const url = new URL(page.url());
    if (url.origin !== new URL(this.serviceURL).origin || url.username || url.password || /\/(?:auth|oauth|login|signin|callback)(?:\/|$)/i.test(url.pathname)) return null;
    url.hash = '';
    return url.href;
  }
  async setConcurrency(count, signal) {
    if (![1, 2, 3, 5, 10].includes(count)) throw fail('MUSE_CONCURRENCY_INVALID', 'Chọn 1, 2, 3, 5 hoặc 10 luồng.', 400);
    if (this.reserved || this.workers.size) throw fail('MUSE_CHAT_BUSY', 'Đợi các cảnh hoàn tất trước khi đổi số luồng.', 409);
    this.maxConcurrency = 1; this.parallelRoutes = [];
    if (count === 1) return { executionConcurrency: 1, message: 'Đã chọn một luồng. Các cảnh được xử lý lần lượt.' };
    await this.open(); await this.refreshActive();
    if (!this.account(1).authenticated) throw fail('MUSE_LOGIN_REQUIRED', 'Đăng nhập Muse và kiểm tra phiên trước khi bật song song.', 401);
    const owned = this.active;
    const pages = [];
    const routes = new Set();
    const stop = () => { for (const page of pages) void (owned.destroyWorkerPage ? owned.destroyWorkerPage(page) : page.close()).catch(() => {}); };
    signal.addEventListener('abort', stop, { once: true });
    try {
      for (let index = 0; index < count; index++) {
        signal.throwIfAborted();
        const page = owned.createWorkerPage ? await owned.createWorkerPage() : await owned.context.newPage();
        pages.push(page); signal.throwIfAborted();
        await page.goto(this.workerURL(), { waitUntil: 'domcontentloaded', timeout: 45000 });
        if (!this.conversationURL(page) || !await this.authenticated(page)) throw fail('MUSE_LOGIN_REQUIRED', 'Chưa xác minh được phiên trong trang luồng riêng.', 401);
        const before = this.conversationURL(page);
        const entry = await this.newChatControl(page);
        if (!entry) throw fail('MUSE_PARALLEL_UNVERIFIED', 'Muse hiện không có nút mở hội thoại riêng. Giữ một luồng để tránh trộn ảnh. Chưa gửi prompt tạo nội dung.', 409);
        await entry.click({ timeout: 5000 });
        await page.waitForURL(url => {
          url.hash = ''; return url.origin === new URL(this.serviceURL).origin && url.href !== before;
        }, { timeout: 5000 }).catch(() => { throw fail('MUSE_PARALLEL_UNVERIFIED', 'New chat chưa cung cấp địa chỉ hội thoại riêng. Chưa xác minh được chạy song song; giữ một luồng. Chưa gửi prompt tạo nội dung.', 409); });
        const route = this.conversationURL(page);
        const editor = await this.waitForComposer(page);
        const handle = await editor.elementHandle();
        let frame;
        try { frame = await handle.ownerFrame(); } finally { await handle.dispose(); }
        if (!route || routes.has(route) || (frame && await frame.locator(`${MESSAGES}[data-message-role="user"]`).count())) throw fail('MUSE_PARALLEL_UNVERIFIED', 'Các trang chưa có hội thoại trống độc lập. Giữ một luồng; chưa gửi prompt tạo nội dung.', 409);
        routes.add(route);
      }
      // Reopen every service-created route: do not treat ten tabs of the same
      // root page, or transient New chat placeholders, as independent chats.
      for (const [index, route] of [...routes].entries()) {
        signal.throwIfAborted();
        const page = pages[index];
        await page.goto(route, { waitUntil: 'domcontentloaded', timeout: 45000 });
        await this.waitForComposer(page);
        if (this.conversationURL(page) !== route) throw fail('MUSE_PARALLEL_UNVERIFIED', 'Muse không giữ địa chỉ hội thoại riêng sau khi mở lại. Giữ một luồng; chưa gửi prompt tạo nội dung.', 409);
      }
      signal.throwIfAborted();
      this.parallelRoutes = [...routes].map(url => ({ url, busy: false }));
      this.maxConcurrency = count;
      return { executionConcurrency: count, message: `Đã kiểm tra ${count} địa chỉ hội thoại riêng và bật tối đa ${count} luồng. Chưa render nội dung; Muse vẫn có thể giới hạn tác vụ theo tài khoản.` };
    } finally {
      signal.removeEventListener('abort', stop);
      await Promise.allSettled(pages.map(page => owned.destroyWorkerPage ? owned.destroyWorkerPage(page) : page.close()));
    }
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
    let activatedAt = 0;
    do {
      const editor = await this.findComposer(page);
      if (editor) return editor;
      if (!activated) {
        activated = await this.activateComposerPlaceholder(page, Math.max(1, deadline - Date.now()));
        if (activated) activatedAt = Date.now();
      }
      if (activated && Date.now() - activatedAt >= 500) {
        const initial = await this.initialComposer(page);
        if (initial) return initial;
      }
      if (openConversation && !opened && !activated) {
        const entry = await this.newChatControl(page);
        if (entry) { await entry.click(); opened = true; }
      }
      await pause(Math.min(100, Math.max(1, deadline - Date.now())));
    } while (Date.now() < deadline);
    const details = await this.composerDiagnostics(page);
    throw fail('MUSE_COMPOSER_NOT_READY', `Chưa mở được ô nhập trong cuộc trò chuyện Muse của cảnh này. Chưa gửi prompt. Đã thử kích hoạt ô Message ban đầu: ${activated ? 'có' : 'không'}. Chẩn đoán trang luồng (không chứa nội dung chat): ${JSON.stringify(details)}`, 504);
  }
  async prepareConversation(page, { reuse = false } = {}) {
    const editor = await this.waitForComposer(page, { openConversation: true });
    const handle = await editor.elementHandle();
    let frame;
    try { frame = await handle.ownerFrame(); }
    finally { await handle.dispose(); }
    const users = frame.locator(`${MESSAGES}[data-message-role="user"]`);
    if (!await users.count()) return frame;
    // A Muse account may expose one persistent conversation. Serial requests
    // can safely append a new marked turn; a missing New chat must not block it.
    if (reuse || this.maxConcurrency === 1) return frame;
    const newChat = await this.newChatControl(frame);
    if (!newChat) throw fail('MUSE_NEW_CHAT_UNAVAILABLE', 'Không mở được cuộc trò chuyện riêng. Chưa gửi prompt; Muse cần hỗ trợ các cuộc trò chuyện độc lập để chạy đồng thời.');
    await newChat.click();
    await frame.waitForFunction(selector => document.querySelectorAll(selector).length === 0, `${MESSAGES}[data-message-role="user"]`, { timeout: 15000 });
    await this.waitForComposer(frame);
    return frame;
  }
  async attach(page, image) {
    const editor = await this.findComposer(page) || await this.initialComposer(page) || await this.waitForComposer(page);
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
  takeTurn(signal) {
    signal.throwIfAborted();
    return new Promise((resolve, reject) => {
      const item = {
        start: () => {
          signal.removeEventListener('abort', cancelled);
          this.executing++;
          let released = false;
          resolve(() => {
            if (released) return;
            released = true; this.executing--; this.pumpQueue();
          });
        },
      };
      const cancelled = () => {
        const index = this.queue.indexOf(item);
        if (index >= 0) this.queue.splice(index, 1);
        signal.removeEventListener('abort', cancelled);
        reject(signal.reason);
      };
      signal.addEventListener('abort', cancelled, { once: true });
      this.queue.push(item); this.pumpQueue();
    });
  }
  pumpQueue() {
    while (this.executing < this.maxConcurrency && this.queue.length) this.queue.shift().start();
  }
  async turn(data) {
    this.requireSingleAccount(data.accountId);
    if (this.reserved >= 10) throw fail('MUSE_CONCURRENCY_LIMIT', 'Đã có 10 cảnh đang xử lý hoặc chờ.', 429);
    this.reserved++;
    let release;
    try { release = await this.takeTurn(data.signal); return await this.executeTurn(data); }
    finally { release?.(); this.reserved--; }
  }
  async executeTurn({ accountId, prompt, image, video, output = video ? 'video' : 'text', signal, checkOnly = false, batchId, sceneId, singleLane = false }) {
    this.requireSingleAccount(accountId);
    if (this.workers.size >= 10) throw fail('MUSE_CONCURRENCY_LIMIT', 'Đã có 10 luồng đang chạy trên tài khoản Muse.', 429);
    const key = randomUUID();
    this.workers.set(key, null);
    const progress = { batchId: batchId || null, sceneId: sceneId || null, output, phase: 'preparing', submitted: false, active: true, startedAt: Date.now() };
    this.workerStages.set(key, progress);
    while (this.workerStages.size > 64) {
      const oldest = [...this.workerStages].find(([, stage]) => !stage.active);
      if (!oldest) break;
      this.workerStages.delete(oldest[0]);
    }
    const lease = this.maxConcurrency > 1 && !singleLane ? this.parallelRoutes.find(route => !route.busy) : null;
    if (lease) lease.busy = true;
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
      await page.goto(lease?.url || this.workerURL(), { waitUntil: 'domcontentloaded', timeout: 45000 });
      if (lease && this.conversationURL(page) !== lease.url) {
        this.maxConcurrency = 1; this.parallelRoutes = [];
        throw fail('MUSE_PARALLEL_UNVERIFIED', 'Muse chuyển hội thoại sang địa chỉ khác. Đã về một luồng; chưa gửi prompt của cảnh này.', 409);
      }
      if (new URL(page.url()).origin !== new URL(this.serviceURL).origin) throw fail('MUSE_WORKSPACE_ORIGIN', 'Trang luồng chuyển sang miền khác Muse. Chưa nhập hoặc gửi prompt. Hoàn tất đăng nhập trong tab Muse rồi kiểm tra lại phiên.', 409);
      const workerProbe = await this.inspectAuthentication(page);
      if (!workerProbe.authenticated) {
        Object.assign(this.account(accountId), { authenticated: false, sessionAuthenticated: false, composerReady: false, state: workerProbe.state, connectionMessage: workerProbe.message });
        throw fail(workerProbe.state === 'check_failed' ? 'MUSE_SESSION_CHECK_FAILED' : 'MUSE_LOGIN_REQUIRED', workerProbe.message, workerProbe.state === 'check_failed' ? 503 : 401);
      }
      const conversation = await this.prepareConversation(page, { reuse: Boolean(lease) || singleLane });
      signal.throwIfAborted();
      if (await conversation.locator(STOP).first().isVisible().catch(() => false)) throw fail('MUSE_CHAT_BUSY', 'Cuộc trò chuyện này đang xử lý yêu cầu khác. Chưa gửi prompt.', 409);
      if (checkOnly) return { ready: true, message: 'Đã mở được ô Message trong trang luồng riêng. Chưa gửi prompt hoặc yêu cầu tạo nội dung.', details: await this.composerDiagnostics(page) };
      const result = await this.sendTurn({ page: conversation, prompt, image, output, signal, onSubmit: () => { sending = true; progress.phase = 'sending'; }, onStage: phase => { progress.phase = phase; if (phase === 'submitted') progress.submitted = true; } });
      if (output === 'image' && batchId && sceneId && result.fingerprint) {
        let batch = this.imageBatches.get(batchId);
        if (!batch) {
          batch = new Map(); this.imageBatches.set(batchId, batch);
          while (this.imageBatches.size > 16) this.imageBatches.delete(this.imageBatches.keys().next().value);
        }
        const previous = [...this.imageBatches.values()].map(value => value.get(result.fingerprint)).find(value => value !== undefined && value !== sceneId);
        if (previous !== undefined && previous !== sceneId) throw fail('MUSE_DUPLICATE_MEDIA', `Kết quả ảnh trùng hoàn toàn với cảnh #${previous}. Tool chưa ghi nhận đây là ảnh mới và không tự gửi lại.`, 409);
        batch.set(result.fingerprint, sceneId);
      }
      progress.phase = 'done'; return result;
    } catch (error) {
      progress.phase = signal.aborted ? 'cancelled' : 'error'; throw error;
    } finally {
      progress.active = false;
      signal.removeEventListener('abort', cancelled);
      if (page) await (owned?.destroyWorkerPage ? owned.destroyWorkerPage(page) : page.close()).catch(() => {});
      this.workers.delete(key);
      if (lease) lease.busy = false;
    }
  }
  async checkComposer(signal) { return this.turn({ accountId: 1, checkOnly: true, signal }); }
  async editorText(editor) {
    return comparableText(await editor.evaluate(el => el.tagName === 'TEXTAREA' ? el.value : el.innerText || el.textContent || ''));
  }
  async writeMessage(page, message, signal) {
    let editor = await this.findComposer(page) || await this.initialComposer(page) || await this.waitForComposer(page);
    if ((await this.editorText(editor)).trim()) throw fail('MUSE_DRAFT_EXISTS', 'Ô Message đang có bản nháp. Tool chưa ghi đè hoặc gửi prompt.', 409);
    let ownedText = '';
    const prefix = Array.from(message)[0];
    const expectedText = comparableText(message);
    if (await editor.getAttribute('data-hatch-composer-prehydration-input') === 'true') {
      // Enter the first character through the input element. It may replace the
      // textarea and transfer only this prefix into a hydrated editor.
      await editor.fill(prefix);
      ownedText = comparableText(prefix);
      await pause(100, signal);
    }
    for (let attempt = 0; attempt < 3; attempt++) {
      signal.throwIfAborted();
      editor = await this.findComposer(page) || await this.initialComposer(page) || await this.waitForComposer(page);
      const text = await this.editorText(editor);
      if (text && text !== ownedText && text !== expectedText && text !== comparableText(prefix)) throw fail('MUSE_DRAFT_CHANGED', 'Nội dung ô Message đã thay đổi trong lúc nhập. Chưa nhấn gửi để tránh ghi đè bản nháp.', 409);
      if (text !== expectedText) await editor.fill(message);
      ownedText = expectedText;
      await pause(100, signal);
      const current = await this.findComposer(page) || await this.initialComposer(page) || await this.waitForComposer(page);
      if (await this.editorText(current) === expectedText) return current;
    }
    throw fail('MUSE_EDITOR_CHANGED', 'Muse đổi ô nhập nhưng chưa giữ đủ prompt. Chưa nhấn gửi. Kiểm tra cuộc trò chuyện rồi thử lại.', 409);
  }
  async sendTurn({ page, prompt, image, output, signal, onSubmit, onStage = () => {} }) {
    let editor = await this.findComposer(page) || await this.initialComposer(page) || await this.waitForComposer(page);
    if ((await editor.innerText().catch(() => '')).trim() || (await editor.inputValue().catch(() => '')).trim()) throw fail('MUSE_DRAFT_EXISTS', 'Ô soạn Muse đang có nội dung chưa gửi. Gửi hoặc xóa bản nháp đó trước; tool không ghi đè.', 409);
    if (await editor.locator('xpath=ancestor::*[@data-hatch-composer-root or self::form][1]').locator('img[src^="blob:"]:not([data-message-item] *)').count()) throw fail('MUSE_DRAFT_EXISTS', 'Ô soạn Muse đang có ảnh chưa gửi. Xử lý bản nháp đó trước; tool không gửi kèm ảnh cũ.', 409);
    if (image) await this.attach(page, image);
    signal.throwIfAborted();
    const marker = `studio-request-${randomUUID()}`;
    const message = `${prompt}\n\n[Request marker: ${marker}. Do not include this marker in your reply.]`;
    editor = await this.writeMessage(page, message, signal);
    signal.throwIfAborted();
    onSubmit();
    this.inFlightMarkers.add(marker);
    const deadline = Date.now() + this.timeoutMs;
    const acknowledgementDeadline = Date.now() + Math.min(this.submitTimeoutMs, this.timeoutMs);
    let lastText = '';
    let stableSince = Date.now();
    let acknowledged = false;
    try {
      await editor.press('Enter');
      while (Date.now() < deadline) {
        await pause(this.pollMs, signal);
        if (this.unsafeMarkers.has(marker)) throw fail('MUSE_SHARED_CONVERSATION', 'Các luồng Muse đang dùng chung hội thoại. Đã dừng nhận kết quả để tránh ghép nhầm; không tự gửi lại.', 409);
        const result = await page.evaluate(({ messages, stop, notice, marker, otherMarkers }) => {
          const visible = el => Boolean(el && el.getClientRects().length);
          const nodes = Array.from(document.querySelectorAll(messages));
          const anchor = nodes.findLastIndex(node => node.getAttribute('data-message-role') === 'user' && node.textContent.includes(marker));
          const nextUser = anchor < 0 ? -1 : nodes.findIndex((node, index) => index > anchor && node.getAttribute('data-message-role') === 'user');
          const replies = anchor < 0 ? [] : nodes.slice(anchor + 1, nextUser < 0 ? undefined : nextUser).filter(node => node.getAttribute('data-message-role') === 'assistant');
          const shared = nodes.some(node => node.getAttribute('data-message-role') === 'user' && otherMarkers.some(other => node.textContent.includes(other)));
          const videos = replies.flatMap(node => Array.from(node.querySelectorAll('video'))).filter(el => el.readyState >= 1 && el.currentSrc).map(el => ({ src: el.currentSrc, duration: el.duration, width: el.videoWidth, height: el.videoHeight }));
          const images = replies.flatMap(node => Array.from(node.querySelectorAll('img'))).filter(el => !el.closest('video') && el.complete && el.naturalWidth >= 128 && el.naturalHeight >= 128).map(el => ({ src: el.currentSrc || el.src, width: el.naturalWidth, height: el.naturalHeight }));
          const error = replies.flatMap(node => Array.from(node.querySelectorAll(notice))).find(visible);
          return { anchored: anchor >= 0, shared, interrupted: nextUser >= 0, text: replies.map(node => node.innerText).join('\n\n').trim(), videos, images,
            streaming: visible(document.querySelector(stop)), error: error?.innerText || '' };
        }, { messages: MESSAGES, stop: STOP, notice: NOTICE, marker, otherMarkers: [...this.inFlightMarkers].filter(other => other !== marker) });
        if (result.shared || (result.interrupted && !result.images.length && !result.videos.length && !result.text)) {
          for (const active of this.inFlightMarkers) this.unsafeMarkers.add(active);
          this.maxConcurrency = 1;
          throw fail('MUSE_SHARED_CONVERSATION', 'Một hội thoại nhận nhiều yêu cầu xen kẽ. Tool dừng để tránh lấy nhầm ảnh; các lần sau sẽ xử lý lần lượt. Không tự gửi lại.', 409);
        }
        if (result.error) throw fail('MUSE_GENERATION_ERROR', result.error);
        if (result.anchored && !acknowledged) { acknowledged = true; onStage('submitted'); }
        if (!result.anchored && !result.streaming && Date.now() >= acknowledgementDeadline) throw fail('MUSE_SUBMIT_NOT_ACKNOWLEDGED', 'Muse chưa xác nhận đã nhận prompt sau thao tác gửi. Tool không tự gửi lại. Mở cuộc trò chuyện kiểm tra trước khi thử lại để tránh tạo trùng.', 504);
        if (result.text !== lastText) { lastText = result.text; stableSince = Date.now(); }
        if (output === 'text' && result.anchored && result.text && !result.streaming && Date.now() - stableSince >= this.quietMs) return { text: result.text };
        const media = output === 'video' ? result.videos[0] : output === 'image' ? result.images[0] : null;
        if (media && !result.streaming) {
          onStage('downloading');
          const base64 = await page.evaluate(async ({ src, output }) => {
            const url = new URL(src, location.href);
            if (!['https:', 'blob:', 'data:'].includes(url.protocol) && !(url.protocol === 'http:' && url.hostname === '127.0.0.1')) throw new Error('Unsupported media URL');
            const response = await fetch(url.href);
            if (!response.ok) throw new Error('Video download failed');
            let blob = await response.blob();
            if (!blob.size || blob.size > 100 * 1024 * 1024) throw new Error('Video must be between 1 byte and 100 MB');
            let fingerprint, width, height;
            if (output === 'image') {
              const bitmap = await createImageBitmap(blob);
              try {
                width = bitmap.width; height = bitmap.height;
                if (!width || !height || width * height > 33554432) throw new Error('Image dimensions exceed limit');
                const canvas = document.createElement('canvas'); canvas.width = width; canvas.height = height;
                const context = canvas.getContext('2d'); context.drawImage(bitmap, 0, 0);
                const pixels = context.getImageData(0, 0, width, height).data;
                const digest = await crypto.subtle.digest('SHA-256', pixels.buffer);
                fingerprint = `${width}x${height}:` + [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, '0')).join('');
                const signature = new Uint8Array(await blob.slice(0, 8).arrayBuffer());
                const isPNG = [137,80,78,71,13,10,26,10].every((byte, index) => signature[index] === byte);
                blob = isPNG ? new Blob([blob], { type: 'image/png' }) : await new Promise((resolve, reject) => canvas.toBlob(value => value ? resolve(value) : reject(new Error('PNG export failed')), 'image/png'));
              } finally { bitmap.close(); }
            }
            return await new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve({ base64: String(reader.result).split(',')[1], mimeType: blob.type, fingerprint, width, height }); reader.onerror = reject; reader.readAsDataURL(blob); });
          }, { src: media.src, output }).catch(() => { throw fail('MUSE_MEDIA_UNREADABLE', 'Chưa tải hoặc giải mã được tệp Muse trả về. Tool không xuất tệp hỏng; mở lịch sử Muse để kiểm tra.', 502); });
          signal.throwIfAborted();
          return { ...base64, mimeType: base64.mimeType?.startsWith(`${output}/`) ? base64.mimeType : output === 'image' ? 'image/png' : 'video/mp4', metadata: { ...(output === 'video' ? { duration: media.duration } : {}), width: base64.width || media.width, height: base64.height || media.height } };
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
    } finally { this.inFlightMarkers.delete(marker); this.unsafeMarkers.delete(marker); }
  }
  async generateVideo(data, signal) {
    const referenceInstruction = data.sourceMode === 'image' ? 'Animate the attached image as the starting frame.' : data.referenceImage ? 'Use the attached image as a character reference, not as an unrelated example.' : 'Create the video from the text prompt.';
    const prompt = `Use your video-generation tool to create exactly one new video, not a link to an existing example. Requested model: ${data.modelDisplayName}. Requested duration: ${data.durationSeconds} seconds, aspect ratio: ${data.aspectRatio}, resolution: ${data.resolution}. If these capabilities are unavailable, explain that clearly. ${referenceInstruction} ${data.characterLock !== false ? 'Preserve the referenced character identity and appearance across scenes.' : 'Follow this scene prompt independently; character consistency is not requested.'}\nScene:\n${data.prompt}`;
    return this.turn({ accountId: data.accountId, prompt, image: data.referenceImage, video: true, signal, batchId: data.batchId, sceneId: data.sceneId, singleLane: data.singleLane });
  }
  async generateImage(data, signal) {
    const longEdge = data.resolution === '4k' ? 3840 : 2560;
    const dimensions = data.aspectRatio === '9:16' ? `${Math.round(longEdge * 9 / 16)}x${longEdge}` : `${longEdge}x${Math.round(longEdge * 9 / 16)}`;
    const useReference = data.characterLock !== false && data.referenceImage;
    const prompt = `Use your image-generation tool to create exactly one new image for this scene. Requested native output: ${data.resolution.toUpperCase()} (${dimensions} pixels), aspect ratio ${data.aspectRatio}. Return the generated image, not a stock image or an old response. Do not claim a higher resolution than the image actually has. ${useReference ? 'Use the attached portrait as a character reference; preserve identity, face and appearance consistently.' : data.characterLock !== false ? 'Follow the character description in this prompt. No portrait is attached; cross-scene identity is not guaranteed without a reference.' : 'Follow this prompt independently. Do not reuse characters or appearance from earlier scenes unless the prompt explicitly requests them.'}\nScene:\n${data.prompt}`;
    return this.turn({ accountId: data.accountId, prompt, image: useReference || undefined, output: 'image', signal, batchId: data.batchId, sceneId: data.sceneId, singleLane: data.singleLane });
  }
  async generateText(data, signal) { return this.turn({ accountId: data.accountId, prompt: data.prompt, video: false, signal, batchId: data.batchId, sceneId: data.sceneId, singleLane: data.singleLane }); }
}
