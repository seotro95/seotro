import {MAX_SLOTS,MAX_ACCOUNT_LANES,isLaneCount,RENDER_TIMEOUT_MS} from './limits.mjs';
import {SubmitGroups} from './submit-groups.mjs';
import { chromium } from 'playwright-core';
import { existsSync } from 'node:fs';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { readMuseBalance } from './muse-balance.mjs';
import {replyProblem,replyPreview,replyStarted} from './muse-reply.mjs';
import{mediaQueue,MediaQueue}from'./media-queue.mjs';
import{readPageAttachment}from'./muse-attachment.mjs';
import{ChatBatches}from'./chat-batches.mjs';
import{inspectBatchDOM}from'./muse-batch-dom.mjs';
import{findSavedBatch}from'./muse-batch-history.mjs';

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
const NEW_CHAT = /^(new chat|new conversation|new thread|cuộc trò chuyện mới|cuộc hội thoại mới|trò chuyện mới|chat mới|bắt đầu trò chuyện)(?:\s*(?:\([^)]{1,30}\)|\[[^\]]{1,30}\]|(?:ctrl|cmd|alt|⌘)[+\s].{0,20}))?$/i;
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
  constructor({ profileRoot, accountProfile, serviceURL = 'https://muse.ai/', launchOptions, sessionFactory, onVerified, timeoutMs = RENDER_TIMEOUT_MS, pollMs = 500, quietMs = 1500, composerTimeoutMs = 45000, submitTimeoutMs = 15000, replyQuietMs = 1500, maxConcurrency = 1 } = {}) {
    this.nativeFileQueue=new MediaQueue(1);
    this.profileRoot = profileRoot;
    this.serviceURL = serviceURL;
    this.launchOptions = launchOptions;
    this.sessionFactory = sessionFactory;
    this.onVerified=onVerified;
    this.workers = new Map();
    this.workerStages = new Map();
    this.opening = null;
    this.timeoutMs = timeoutMs;
    this.pollMs = pollMs;
    this.quietMs = quietMs;
    this.composerTimeoutMs = composerTimeoutMs;
    this.submitTimeoutMs = submitTimeoutMs;
    this.replyQuietMs=replyQuietMs;
    this.maxConcurrency = Math.max(1, Math.min(MAX_ACCOUNT_LANES, maxConcurrency));
    this.reserved = 0;
    this.executing = 0;
    this.queue = [];
    this.inFlightMarkers = new Set();
    this.unsafeMarkers = new Set();
    this.imageBatches = new Map();
    this.parallelRoutes = [];
    this.submitGroups=new SubmitGroups();this.parallelStrategy='workers';this.composerQueue=[];this.composerBusy=false;this.sharedSignals=new Map();this.sharedStopPromise=null;
    this.pendingCaptions=new Set();this.composerOwners=new WeakMap();this.chatBatches=new ChatBatches((rows,group)=>this.sendSharedBatch(rows,group),{limit:()=>Math.min(6,this.maxConcurrency)});
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
  async close({preserveBatch=false}={}) {
    if(!preserveBatch)this.chatBatches.cancelAll();
    this.submitGroups.clear();
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
    await this.close({preserveBatch:true});
    if (this.sessionFactory) {
      const owned = await this.sessionFactory();
      this.active = { id, ...owned };
      this.account(id).state = 'login_open';
      if (show) owned.showLogin?.();
      try { await owned.page.goto(owned.initialURL||this.serviceURL, { waitUntil: 'domcontentloaded', timeout: 45000 }); }
      catch { throw fail('MUSE_CONNECTION_FAILED', 'Không tải được trang Muse. Kiểm tra Internet rồi bấm Tải lại Muse; phiên cũ vẫn được giữ.', 503); }
      await owned.restoreStorage?.();
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
  async refreshActive({ background = false,includeDetails=true } = {}) {
    if(background&&this.active?.isLoginVisible?.())return;
    const page=this.active?.page;
    if(this.refreshing&&this.refreshingPage===page)return this.refreshing;
    const pending=this.refreshSession({background,includeDetails});this.refreshing=pending;this.refreshingPage=page;
    try{return await pending}finally{if(this.refreshing===pending){this.refreshing=null;this.refreshingPage=null}}
  }
  async refreshSession({ background = false,includeDetails=true } = {}) {
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
    const workspaceMissing=probe.authenticated&&!composerReady&&account.state==='workspace_unavailable';
    account.state = workspaceMissing?'workspace_unavailable':probe.authenticated ? 'ready' : probe.state;
    account.connectionMessage = workspaceMissing?account.connectionMessage:probe.authenticated ? 'Phiên Muse đã được xác minh. Tool mở ô soạn riêng khi bạn bấm tạo từng cảnh hoặc cả bộ.' : probe.message;
    if(includeDetails)account.balance = account.authenticated ? await readMuseBalance(active.page) : null;
    if(account.authenticated){const saved=this.onVerified?.();if(includeDetails)await saved;else void saved?.catch(()=>{})}
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
        for (let index = 0, count = await candidates.count(); index < count; index++){const editor=candidates.nth(index);this.composerOwners.set(editor,frame);matches.push(editor)}
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
      for (let index = 0, count = await candidates.count(); index < count; index++){const editor=candidates.nth(index);this.composerOwners.set(editor,frame);matches.push(editor)}
    }
    if (matches.length > 1) throw fail('MUSE_COMPOSER_AMBIGUOUS', 'Có nhiều ô Message ban đầu trong trang Muse. Chưa kích hoạt hoặc gửi prompt để tránh chọn nhầm ô.');
    return matches[0] || null;
  }
  async newChatControl(page) {
    for (const frame of await this.composerFrames(page)) {
      const entry = frame.getByRole('button', { name: NEW_CHAT }).or(frame.getByRole('link', { name: NEW_CHAT })).filter({ visible: true }).first();
      if (await entry.count()) return entry;
      const icon=frame.locator('[data-testid="new-chat-button"], [data-testid="new-conversation-button"], [data-testid="hatch-new-chat-button"], button[title="New chat" i], a[href$="/chat/new"], a[href$="/chats/new"]').filter({visible:true}).first();
      if(await icon.count())return icon;
    }
    return null;
  }
  async ensureComposerReady(signal){
    signal.throwIfAborted();await this.open(1);await this.refreshActive({includeDetails:false});
    const account=this.account(1),page=this.active.page;
    if(!account.authenticated)throw fail('MUSE_LOGIN_REQUIRED',account.connectionMessage||'Hoàn tất đăng nhập Muse trước khi chạy.',401);
    const started=Date.now(),budget=Math.min(this.composerTimeoutMs,15000);let reloaded=false,opened=false;
    try{
      do{
        signal.throwIfAborted();
        if(await this.findComposer(page)||await this.initialComposer(page)){Object.assign(account,{composerReady:true,state:'ready'});return {ready:true};}
        let draft=false;for(const frame of await this.composerFrames(page))if(await frame.evaluate(()=>[...document.querySelectorAll('textarea,[contenteditable="true"],[contenteditable="plaintext-only"]')].some(node=>!node.closest('[data-message-item]')&&String(node.value||node.innerText||'').trim())).catch(()=>true)){draft=true;break;}
        if(!draft&&!opened){
          const entry=await this.newChatControl(page);
          if(entry){await entry.click({timeout:Math.max(1,Math.min(3000,started+budget-Date.now()))});opened=true;continue;}
          const launch=page.getByRole('link',{name:/^(?:(?:open|launch|enter|go to)(?: the| your)? (?:muse|studio|workspace|app)|mở studio|vào studio|mở ứng dụng|vào ứng dụng)$/i}).filter({visible:true}).first();
          if(await launch.count()){
            const href=await launch.getAttribute('href'),target=new URL(href||'',page.url());
            if(target.origin===new URL(this.serviceURL).origin&&!target.username&&!target.password&&!target.search&&(/^\/(?:app|studio|workspace|chats?)(?:\/new)?\/?$/.test(target.pathname)||(target.pathname==='/'&&/^#\/(?:app|studio|workspace|chats?)(?:\/new)?\/?$/.test(target.hash)))){await page.goto(target.href,{waitUntil:'domcontentloaded',timeout:Math.max(1,started+budget-Date.now())});opened=true;continue;}
          }
        }
        if(!draft&&!reloaded&&this.conversationURL(page)&&Date.now()-started>=Math.min(1000,budget/3)&&!await page.locator(STOP).first().isVisible().catch(()=>false)){
          reloaded=true;await page.reload({waitUntil:'domcontentloaded',timeout:Math.max(1,started+budget-Date.now())});continue;
        }
        await pause(Math.min(100,Math.max(1,started+budget-Date.now())),signal);
      }while(Date.now()-started<budget);
      const details=await this.composerDiagnostics(page);
      throw fail('MUSE_COMPOSER_NOT_READY',`Phiên đã xác thực nhưng chưa có ô Message, chưa gửi prompt. Mở đúng workspace trong Đăng nhập Muse trong tool rồi kiểm tra lại. Đã mở lối vào đang hiển thị: ${opened}; tải lại: ${reloaded}. Chẩn đoán: ${JSON.stringify(details)}`,409);
    }catch(error){Object.assign(account,{composerReady:false,state:'workspace_unavailable',connectionMessage:error.message});throw error;}
  }
  workerURL() {
    // Use the user's verified app route, rather than sending every worker back
    // to a marketing/landing page. OAuth query parameters are never copied.
    return this.conversationURL(this.active.page)||this.serviceURL;
  }
  async createWorkerPage(){
    const owned=this.active;
    const origin=new URL(this.serviceURL).origin;
    const storage=await owned.page.evaluate(origin=>location.origin===origin?Object.fromEntries(Object.entries(sessionStorage)): {},origin).catch(()=>({}));
    const page=owned.createWorkerPage?await owned.createWorkerPage():await owned.context.newPage();
    await page.addInitScript(({origin,storage})=>{if(location.origin===origin)for(const [key,value]of Object.entries(storage))if(typeof value==='string'&&sessionStorage.getItem(key)===null)sessionStorage.setItem(key,value)},{origin,storage});
    return page;
  }
  async closePreparedPages(){
    const owned=this.active;const lanes=this.parallelRoutes;this.parallelRoutes=[];
    await Promise.allSettled(lanes.filter(lane=>lane.page&&!lane.page.isClosed()).map(lane=>owned?.destroyWorkerPage?owned.destroyWorkerPage(lane.page):lane.page.close()));
  }
  get parallelReady(){return this.parallelStrategy==='shared-conversation'||this.maxConcurrency===1||this.parallelRoutes.length===this.maxConcurrency&&this.parallelRoutes.every(lane=>lane.page&&!lane.page.isClosed())}
  async freshConversation(page,signal){
    const entry=await this.newChatControl(page);
    if(!entry)throw fail('MUSE_NEW_CHAT_UNAVAILABLE','Chưa tìm được nút mở hội thoại mới riêng cho từng ô.',409);
    signal.throwIfAborted();await entry.click({timeout:5000});
    const editor=await this.waitForComposer(page);const handle=await editor.elementHandle();let frame;
    try{frame=await handle.ownerFrame()}finally{await handle.dispose()}
    if(!frame)throw fail('MUSE_COMPOSER_NOT_READY','Chưa tìm được khung soạn cho ô riêng.',409);
    await frame.waitForFunction(selector=>!document.querySelectorAll(selector).length,`${MESSAGES}[data-message-role="user"]`,{timeout:10000});
    if((await this.editorText(editor)).trim()||await frame.locator(STOP).first().isVisible().catch(()=>false))throw fail('MUSE_PARALLEL_UNVERIFIED','Hội thoại mới chưa trống hoặc vẫn có lượt khác. Chưa gửi prompt.',409);
    return frame;
  }

  conversationURL(page) {
    const url = new URL(page.url());
    if (url.origin !== new URL(this.serviceURL).origin || url.username || url.password || /\/(?:auth|oauth|login|signin|callback)(?:\/|$)/i.test(url.pathname)) return null;
    if(/[?&#](?:access_token|id_token|code|state)=/i.test(url.search+url.hash))return null;
    return url.href;
  }
  async setConcurrency(count, signal, {allowSharedFastPath=false}={}) {
    if(!isLaneCount(count))throw fail('MUSE_CONCURRENCY_INVALID','Chọn từ 1 đến 10 ô mỗi tài khoản.',400);
    if(this.reserved||this.workers.size)throw fail('MUSE_CHAT_BUSY','Đợi các cảnh hoàn tất trước khi đổi số luồng.',409);
    await this.closePreparedPages();this.parallelStrategy='workers';this.maxConcurrency=1;this.concurrencyProbe={requested:count,checked:0,state:'checking'};
    if(count===1){await this.ensureComposerReady(signal);this.concurrencyProbe.state='ready';return {executionConcurrency:1,message:'Đã xác minh ô Message; sẵn sàng chạy lần lượt.'}}
    await this.open();await this.refreshActive();
    if(!this.account(1).authenticated)throw fail('MUSE_LOGIN_REQUIRED','Đăng nhập Muse và kiểm tra phiên trước khi bật song song.',401);
    // A verified single-chat page without New chat cannot provide independent
    // worker conversations. Avoid opening four redundant copies per account.
    if(allowSharedFastPath&&!await this.newChatControl(this.active.page)){this.concurrencyProbe.state='unavailable';throw Object.assign(fail('MUSE_PARALLEL_UNVERIFIED','Trang hiện tại dùng một cuộc trò chuyện; chuyển sang gửi trong cùng chat.',409),{parallelReason:'MUSE_NEW_CHAT_UNAVAILABLE'})}
    const owned=this.active;const pages=new Set();const lanes=[];let next=0;let failure;
    // Let in-flight page creation settle before closing any probe. Closing
    // targets while Chromium is creating sibling targets can stall on Windows.
    const stop=()=>{failure||=signal.reason||fail('ABORTED','Đã dừng chuẩn bị tài khoản.')};
    const dispose=async()=>{for(const page of pages)await(owned.destroyWorkerPage?owned.destroyWorkerPage(page):page.close()).catch(()=>{})};
    signal.addEventListener('abort',stop,{once:true});
    const probe=async()=>{while(!failure&&next<count){next++;let page;try{
      signal.throwIfAborted();page=await this.createWorkerPage();pages.add(page);if(failure)return;signal.throwIfAborted();
      await page.goto(this.workerURL(),{waitUntil:'domcontentloaded',timeout:45000});
      if(!this.conversationURL(page)||!await this.authenticated(page))throw fail('MUSE_PARALLEL_UNVERIFIED','Trang luồng riêng chưa dùng được phiên Muse đã đăng nhập; cần dùng lại trang đăng nhập để chạy tuần tự.',409);
      await this.freshConversation(page,signal);
      lanes.push({page,url:this.conversationURL(page),busy:false});this.concurrencyProbe.checked++;
    }catch(error){if(!failure)failure=error}}};
    try{
      await Promise.all(Array.from({length:Math.min(4,count)},probe));if(failure)throw failure;signal.throwIfAborted();
      this.parallelRoutes=lanes;this.maxConcurrency=count;this.concurrencyProbe.state='ready';
      return {executionConcurrency:count,message:`Đã chuẩn bị sẵn ${count} trang Muse riêng; các ô gửi cùng lượt sau khi nhập đủ prompt. Không đợi kết quả ô trước.`};
    }catch(error){await dispose();this.concurrencyProbe.state='unavailable';if(signal.aborted||/MUSE_LOGIN_REQUIRED|MUSE_SESSION_|MUSE_CHAT_BUSY/.test(error.message))throw error;throw Object.assign(fail('MUSE_PARALLEL_UNVERIFIED','Chưa chuẩn bị được các trang Muse riêng để chạy đồng thời.',409),{parallelReason:error.message.split(':')[0]})}finally{signal.removeEventListener('abort',stop)}
  }
  async useSharedConversation(count,signal){
    if(!isLaneCount(count))throw fail('MUSE_CONCURRENCY_INVALID','Chọn 1–10 ô.',400);
    signal.throwIfAborted();await this.closePreparedPages();await this.refreshActive({includeDetails:false});if(!this.account(1).authenticated)throw fail('MUSE_LOGIN_REQUIRED','Cần đăng nhập Muse.',401);
    const frame=await this.prepareConversation(this.active.page,{reuse:true});const editor=await this.findComposer(frame)||await this.initialComposer(frame)||await this.waitForComposer(frame);if((await this.editorText(editor)).trim())throw fail('MUSE_DRAFT_EXISTS','Ô Muse có bản nháp; chưa ghi đè.',409);
    this.parallelStrategy='shared-conversation';this.maxConcurrency=Math.min(count,6);this.concurrencyProbe={requested:count,checked:this.maxConcurrency,state:'ready',strategy:'shared-conversation'};
    return {executionConcurrency:this.maxConcurrency,parallelStrategy:'shared-conversation',message:`Gửi ${this.maxConcurrency} tin nhắn liên tiếp trong cùng cuộc trò chuyện, không đợi kết quả trước. Các ô còn lại chờ.`};
  }
  acquireComposer(signal){
    signal.throwIfAborted();return new Promise((resolve,reject)=>{
      const row={start:()=>{signal.removeEventListener('abort',row.abort);this.composerBusy=true;let released=false;resolve(()=>{if(released)return;released=true;this.composerBusy=false;this.pumpComposer()})},abort:()=>{const index=this.composerQueue.indexOf(row);if(index>=0)this.composerQueue.splice(index,1);signal.removeEventListener('abort',row.abort);reject(signal.reason)}};
      signal.addEventListener('abort',row.abort,{once:true});this.composerQueue.push(row);this.pumpComposer();
    });
  }
  pumpComposer(){if(!this.composerBusy&&this.composerQueue.length)this.composerQueue.shift().start()}
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
    const frame=this.composerOwners.get(editor);
    if(!frame)throw fail('MUSE_COMPOSER_NOT_READY','Chưa xác định được khung chứa ô Message. Chưa gửi prompt.',409);
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
    if (this.reserved >= MAX_SLOTS) throw fail('MUSE_CONCURRENCY_LIMIT', 'Đã có 400 cảnh đang xử lý hoặc chờ.', 429);
    if(data.submissionGroup?.size>this.maxConcurrency)throw fail('MUSE_PARALLEL_UNVERIFIED','Số ô cùng lượt vượt số trang Muse đã chuẩn bị. Chưa gửi prompt.',409);
    const submitBarrier=this.parallelStrategy==='shared-conversation'?null:this.submitGroups.register(data.submissionGroup,data.batchId,data.sceneId,data.signal);
    this.reserved++;
    let release;
    try { release = await this.takeTurn(data.signal); return await this.executeTurn({...data,submitBarrier}); }
    catch(error){if(!data.signal.aborted)submitBarrier?.fail(error);throw error}
    finally { release?.(); this.reserved--; }
  }
  async executeTurn({ accountId, prompt, image, video, output = video ? 'video' : 'text', signal, checkOnly = false, batchId, sceneId, singleLane = false, submitBarrier,submissionGroup }) {
    this.requireSingleAccount(accountId);
    if (this.workers.size >= MAX_ACCOUNT_LANES) throw fail('MUSE_CONCURRENCY_LIMIT', 'Đã chạy đủ 10 ô trên tài khoản Muse.', 429);
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
    const sharedConversation=this.parallelStrategy==='shared-conversation'&&output!=='text';
    const parallelAttempt=this.maxConcurrency>1&&(!singleLane||sharedConversation);
    let page; let owned; let sending = false;let reuseLogin=false;
    const cancelled = () => { if (page && !sending&&!reuseLogin) void (owned?.destroyWorkerPage ? owned.destroyWorkerPage(page) : page.close()).catch(() => {}); };
    signal.addEventListener('abort', cancelled, { once: true });
    try {
      signal.throwIfAborted();
      await this.open(accountId);
      owned = this.active;
      progress.phase='checking-session';
      await this.refreshActive({includeDetails:false});
      if (!this.account(accountId).authenticated) {
        const account = this.account(accountId);
        const code = account.state === 'check_failed' ? 'MUSE_SESSION_CHECK_FAILED' : 'MUSE_LOGIN_REQUIRED';
        throw fail(code, account.connectionMessage || 'Đăng nhập tài khoản Muse trong tool, rồi bấm Kiểm tra phiên.', code === 'MUSE_LOGIN_REQUIRED' ? 401 : 503);
      }
      signal.throwIfAborted();
      reuseLogin=singleLane&&!owned.page.isClosed()&&new URL(owned.page.url()).origin===new URL(this.serviceURL).origin;
      progress.phase='opening-page';
      page=reuseLogin?owned.page:lease?.page&&!lease.page.isClosed()?lease.page:await this.createWorkerPage();
      this.workers.set(key,page);signal.throwIfAborted();
      if(!reuseLogin&&page.url().startsWith('about:blank')){
        await page.goto(this.workerURL(),{waitUntil:'domcontentloaded',timeout:45000});
        if(lease)await this.freshConversation(page,signal);
      }
      if (new URL(page.url()).origin !== new URL(this.serviceURL).origin) throw fail('MUSE_WORKSPACE_ORIGIN', 'Trang luồng chuyển sang miền khác Muse. Chưa nhập hoặc gửi prompt. Hoàn tất đăng nhập trong tab Muse rồi kiểm tra lại phiên.', 409);
      const workerProbe = reuseLogin?{authenticated:true}:await this.inspectAuthentication(page);
      if (!workerProbe.authenticated) {
        if(parallelAttempt)throw fail('MUSE_PARALLEL_UNVERIFIED','Trang chạy song song chưa xác minh được phiên; chuyển sang dùng phiên đang đăng nhập.',409);
        Object.assign(this.account(accountId), { authenticated: false, sessionAuthenticated: false, composerReady: false, state: workerProbe.state, connectionMessage: workerProbe.message });
        throw fail(workerProbe.state === 'check_failed' ? 'MUSE_SESSION_CHECK_FAILED' : 'MUSE_LOGIN_REQUIRED', workerProbe.message, workerProbe.state === 'check_failed' ? 503 : 401);
      }
      const conversationKey=page;
      if(this.pendingCaptions.has(conversationKey)&&!sharedConversation){
        progress.phase='waiting-provider';const deadline=Date.now()+this.timeoutMs;
        for(;;){signal.throwIfAborted();let pending=false;for(const frame of await this.composerFrames(page))if(await frame.locator(STOP).first().isVisible().catch(()=>false)){pending=true;break}if(!pending)break;if(Date.now()>=deadline)throw fail('MUSE_CHAT_BUSY','Muse còn xử lý lượt trước. Video trước đã được lưu; chưa gửi prompt mới.',409);await pause(250,signal)}
        this.pendingCaptions.delete(conversationKey);
      }
      progress.phase='waiting-editor';
      const conversation = await this.prepareConversation(page, { reuse: Boolean(lease) || singleLane });
      signal.throwIfAborted();
      if (!sharedConversation&&await conversation.locator(STOP).first().isVisible().catch(() => false)) throw fail('MUSE_CHAT_BUSY', 'Cuộc trò chuyện này đang xử lý yêu cầu khác. Chưa gửi prompt.', 409);
      if (checkOnly) return { ready: true, message: 'Đã mở được ô Message trong trang luồng riêng. Chưa gửi prompt hoặc yêu cầu tạo nội dung.', details: await this.composerDiagnostics(page) };
      const result = await this.sendTurn({ page: conversation, prompt, image, output, signal,batchId,sceneId,submissionGroup,sharedConversation,trackAtStart:reuseLogin, onSubmit: () => { sending = true; progress.phase = 'sending';progress.sentAt=Date.now(); }, beforeSubmit:submitBarrier?()=>submitBarrier.ready():undefined,onObservation: details=>{progress.observation=details;}, onStage: phase => { progress.phase = phase; if (phase === 'submitted'){progress.submitted = true;progress.submittedAt=Date.now();} } });
      if(result.captionPending)this.pendingCaptions.add(conversationKey);
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
      progress.phase = signal.aborted ? /TIMEOUT/.test(signal.reason?.message||'')?'timeout':'cancelled' : 'error';
      const wrapped=Object.assign(new Error(error.message),{status:error.status,notSubmitted:!sending,safeSerialRetry:error.safeSerialRetry===true,parallelFailure:parallelAttempt&&!signal.aborted&&((!sending&&!/MUSE_LOGIN_|MUSE_SESSION_|MUSE_WORKSPACE_ORIGIN|MUSE_DRAFT_|MUSE_ATTACHMENT_|MUSE_UPLOAD_/.test(error.message))||/MUSE_SHARED_CONVERSATION|MUSE_PARALLEL_LIMIT|MUSE_SUBMIT_NOT_ACKNOWLEDGED|MUSE_TIMEOUT/.test(error.message))});
      throw signal.aborted?signal.reason:wrapped;
    } finally {
      progress.active = false;
      signal.removeEventListener('abort', cancelled);
      if (page&&!reuseLogin) await (owned?.destroyWorkerPage ? owned.destroyWorkerPage(page) : page.close()).catch(() => {});
      this.workers.delete(key);
      if (lease) {lease.busy = false;lease.page=null;}
      if(page&&!reuseLogin)this.pendingCaptions.delete(page);
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
  async sendSharedBatch(input,group){
    let rows=input.filter(row=>!row.done);let release;let sent=false;let overlapped=false;const downloads=new Set(),attempts=new Map(),unsupportedSince=new Map(),failedSources=new Map(),candidatesFor=new Map(),bindings={};
    const rejectPending=error=>rows.forEach(row=>{if(!row.done)row.reject(error)});
    try{
      release=await this.acquireComposer(group.control.signal);
      for(const row of rows)if(row.signal.aborted)row.reject(row.signal.reason);
      rows=rows.filter(row=>!row.done);if(!rows.length)return;
      if(this.parallelStrategy!=='shared-conversation')throw fail('MUSE_PARALLEL_UNVERIFIED','Đã chuyển sang tuần tự trước khi gửi lượt gộp.',409);
      const page=rows[0].page,output=rows[0].output;const marker=`studio-batch-${randomUUID()}`;
      const budget=Math.min(...rows.map(row=>row.createdAt+this.timeoutMs));const snapshot=await page.evaluate(inspectBatchDOM,{captureOnly:true,output});const baseline=snapshot.keys;
      let editor=await this.findComposer(page)||await this.initialComposer(page)||await this.waitForComposer(page);
      if((await this.editorText(editor)).trim())throw fail('MUSE_DRAFT_EXISTS','Muse đang có bản nháp. Chưa gửi lượt gộp.',409);
      if(await editor.locator('xpath=ancestor::*[@data-hatch-composer-root or self::form][1]').locator('img[src^="blob:"]:not([data-message-item] *)').count())throw fail('MUSE_DRAFT_EXISTS','Muse đang có ảnh trong bản nháp. Tool chưa gửi lượt gộp.',409);
      rows.forEach((row,index)=>row.label=`CLIP_${String(row.sceneId||index+1).padStart(3,'0')}_${marker.slice('studio-batch-'.length, 'studio-batch-'.length+8)}`);
      const prefixes=rows.map(row=>{const at=row.prompt.indexOf('\nScene:\n');return at<0?null:{head:row.prompt.slice(0,at),scene:row.prompt.slice(at+8)}});
      const common=prefixes.every(value=>value&&value.head===prefixes[0]?.head)?prefixes[0].head:'';
      rows.forEach((row,index)=>{row.sourceClip=Number((prefixes[index]?.scene||row.prompt).trim().match(/^CLIP[ _-]*(\d{1,4})\b/i)?.[1])||undefined});
      const tasks=rows.map((row,index)=>`[BEGIN_CLIP ${row.label} ${row.fileToken}]\n${common?prefixes[index].scene:row.prompt}\n[END_CLIP ${row.fileToken}]`).join('\n\n');
      const message=`[${marker}]\nCreate ${rows.length} independent ${output==='video'?'video':'image'} file${rows.length===1?'':'s'} now in this ONE request. Each task below is a separate output; use the available generation tool for every task. ${output==='video'?'Keep the requested duration for EACH video; do not stitch the tasks into one long film.':''} Do not just write a plan or ask whether to start.\nFor each result, put its CLIP label in the same list item or heading as its native attachment or real download link. Preserve the real working URL; never invent file paths or rename files just for tracking. If a task cannot be generated, give its label and concrete reason.\n\n${common?'Apply these instructions to EACH task:\n'+common+'\n\n':''}${tasks}`;
      const maxLength=Number(await editor.getAttribute('maxlength'));if(maxLength>0&&message.length>maxLength)throw fail('MUSE_BATCH_TOO_LONG','Yêu cầu gộp vượt độ dài Muse cho phép. Chưa gửi prompt; chuyển sang từng ô và giữ đủ nội dung.',409);
      if(rows[0].image)await this.attach(page,rows[0].image);
      editor=await this.writeMessage(page,message,group.control.signal);group.control.signal.throwIfAborted();
      for(const row of rows){row.onSubmit();this.sharedSignals.set(row.fileToken,row.signal)}sent=true;
      await editor.press('Enter');
      let acknowledged=false,lastSignature='',stableSince=Date.now();const ackDeadline=Date.now()+Math.min(this.submitTimeoutMs,this.timeoutMs);
      while(Date.now()<budget&&!group.cancelled){
        if(this.sharedSignals.size>rows.length)overlapped=true;
        if(rows.every(row=>row.done))return;
        if([...this.sharedSignals.values()].every(signal=>signal.aborted)){
          if(!this.sharedStopPromise)this.sharedStopPromise=(async()=>{await page.locator(STOP).first().evaluate(button=>button.click(),undefined,{timeout:3000}).catch(()=>{});await pause(200)})();
          await this.sharedStopPromise;for(const row of rows)if(!row.done)row.reject(row.signal.reason||fail('ABORTED','Đã dừng lượt tạo.'));return;
        }
        const state=await page.evaluate(inspectBatchDOM,{marker,rows:rows.map(row=>({fileToken:row.fileToken,label:row.label,sourceClip:row.sourceClip})),baseline,baselineTexts:snapshot.texts,acknowledged,bindings,output,allowScopedLabels:!overlapped,allowSingle:!overlapped&&rows.length===1&&this.sharedSignals.size===1});
        if(state.anchored&&!acknowledged){acknowledged=true;for(const row of rows)if(!row.done)row.onStage('submitted')}
        if(!acknowledged&&Date.now()>=ackDeadline)throw fail('MUSE_SUBMIT_NOT_ACKNOWLEDGED','Muse chưa xác nhận đã nhận yêu cầu gộp. Tool không tự gửi trùng.',504);
        const signature=JSON.stringify([state.text,state.media.map(item=>item.key)]);if(signature!==lastSignature){lastSignature=signature;stableSince=Date.now()}
        const unique=new Set(state.media.filter(item=>!item.uncertain).map(item=>item.owner||item.key)).size;
        for(const row of rows){
          if(row.done)continue;
          row.onObservation?.({checkedAt:new Date().toISOString(),messageAcknowledged:acknowledged,assistantReplies:state.replyCount,visibleVideos:output==='video'?unique:0,visibleImages:output==='image'?unique:0,matchedMedia:Boolean(state.matches[row.fileToken]),matchedCount:Object.keys(state.matches).length,unmatchedCount:state.unclaimed,captionLinked:state.captionLinked,mediaActions:state.media.map(item=>({kind:item.kind,action:item.nativeButton?'download-button':item.nativeDownload?'native-link':'direct-file',protocol:(()=>{try{return new URL(item.src,page.url()).protocol}catch{return 'invalid'}})(),sceneId:Number(rows.find(row=>row.fileToken===item.owner)?.sceneId)||null})),clipLabels:rows.map(item=>({sceneId:item.sceneId,label:item.label,sourceClip:item.sourceClip||null})),unsupportedMedia:state.unsupported.map(item=>({scheme:item.scheme,locationClass:item.locationClass,element:item.element,sceneId:Number(rows.find(row=>row.fileToken===item.owner)?.sceneId)||null})),replyLayout:state.replyLayout,streaming:state.streaming,replyScope:'batch',reply:replyPreview(state.text),batchSize:rows.length,messagesSent:1,waitLimitSeconds:250});
          if(row.signal.aborted)row.onStage('cancelled-provider');else if(state.text&&!state.matches[row.fileToken])row.onStage('reply-received');
          const candidates=[state.matches[row.fileToken],...state.media.filter(item=>item.owner===row.fileToken)].filter(Boolean).filter((item,index,all)=>all.findIndex(value=>value.key===item.key)===index);candidatesFor.set(row,candidates);
          let media=candidates.find(item=>!failedSources.get(row)?.has(item.key));
          if((attempts.get(row)?.count||0)>=2){const control=candidates.find(item=>item.nativeButton&&!failedSources.get(row)?.has(item.key));if(control)media=control;}
          if(!media&&state.rowErrors[row.fileToken]){const message=state.rowErrors[row.fileToken];const code=replyProblem(message)||'MUSE_GENERATION_ERROR';const error=fail(code,`Muse báo lỗi của ${row.label}: ${replyPreview(message)}`,502);if(code==='MUSE_PARALLEL_LIMIT')error.safeSerialRetry=true;row.reject(error);this.sharedSignals.delete(row.fileToken);continue;}
          if(!media&&!state.streaming&&state.rowTexts[row.fileToken]&&Date.now()-stableSince>=this.replyQuietMs){const problem=replyProblem(state.rowTexts[row.fileToken]);if(problem){row.reject(fail(problem,`Muse chưa trả tệp của ${row.label}: ${replyPreview(state.rowTexts[row.fileToken])}`,422));this.sharedSignals.delete(row.fileToken);continue;}}
          const blocked=state.unsupported.filter(item=>item.owner===row.fileToken);
          if(!media&&blocked.length){if(!unsupportedSince.has(row.fileToken))unsupportedSince.set(row.fileToken,Date.now());if(!state.streaming&&Date.now()-unsupportedSince.get(row.fileToken)>=5000&&Date.now()-stableSince>=this.replyQuietMs){row.reject(fail('MUSE_MEDIA_UNREADABLE',`MEDIA_URL_UNSUPPORTED: Liên kết của ${row.label} chưa có nguồn tệp hỗ trợ. Loại liên kết: ${[...new Set(blocked.map(item=>item.scheme+' ('+item.locationClass+', '+item.element+')'))].join(', ')}. Các ô khác tiếp tục; chưa tạo lại yêu cầu.`,502));this.sharedSignals.delete(row.fileToken);continue;}}
          else unsupportedSince.delete(row.fileToken);
          if(!media||downloads.has(row))continue;const last=attempts.get(row);if(last?.key===media.key&&last.nextAt>Date.now())continue;
          if(row.signal.aborted){row.reject(row.signal.reason);this.sharedSignals.delete(row.fileToken);continue;}
          downloads.add(row);row.onStage('downloading');
          void this.downloadMedia(page,{...media,tryMissingControl:(attempts.get(row)?.count||0)>=2},output,row.signal).then(value=>{bindings[row.fileToken]=media.key;row.resolve({...value,captionPending:false});},error=>{
            if(!row.signal.aborted&&(/MEDIA_HTTP_404|MEDIA_EMPTY/.test(error.message)||(media.uncertain&&/MEDIA_RESPONSE_NOT_MEDIA/.test(error.message)))){const count=(attempts.get(row)?.count||0)+1;attempts.set(row,{key:media.key,count,nextAt:Date.now()+Math.min(10000,500*2**Math.min(count,6))});downloads.delete(row);row.onStage('reply-received');return;}const tried=failedSources.get(row)||new Set();tried.add(media.key);failedSources.set(row,tried);if(!row.signal.aborted&&candidatesFor.get(row)?.some(item=>!tried.has(item.key))){downloads.delete(row);row.onStage('reply-received');return;}row.reject(error);
          }).finally(()=>{if(row.done)this.sharedSignals.delete(row.fileToken)});
        }
        // An acknowledged user bubble alone never releases the next chat turn.
        // An explicit started-generation reply also frees the composer for an
        // additional card; it never marks the current result as completed.
        if(release&&!state.streaming&&(Object.keys(state.matches).length||replyStarted(state.text))){release();release=null}
        if(!state.streaming&&!state.media.length&&state.text&&Date.now()-stableSince>=this.replyQuietMs){
          const problem=replyProblem(state.generalText);if(problem){const error=fail(problem,`Muse chưa tạo ${output==='video'?'video':'ảnh'} cho lượt gộp: ${replyPreview(state.generalText)}`,422);if(problem==='MUSE_PARALLEL_LIMIT'&&/no (?:videos?|images?|generations?) (?:were|was|have been|has been) (?:created|started)|did not start any|chưa tạo.*(?:video|ảnh) nào|không tạo được.*(?:video|ảnh) nào/i.test(state.generalText))error.safeSerialRetry=true;throw error;}
        }
        if(!state.streaming&&state.unclaimed&&state.completedRows>=rows.length&&this.sharedSignals.size<=rows.filter(row=>!row.done).length&&Date.now()-stableSince>=Math.max(8000,this.replyQuietMs))throw fail('MUSE_BATCH_UNMATCHED',`Đã thấy ${unique} nguồn media và nhãn hoàn thành nhưng chỉ ghép được ${Object.keys(state.matches).length}/${rows.length} ô. Dùng Nhận lại từ Muse để chỉ lấy tệp đã tạo, không gửi lại prompt.`,409);
        if(!state.streaming&&!state.media.length&&state.unsupported.length&&state.unsupported.every(item=>!item.owner)&&Date.now()-stableSince>=5000)throw fail('MUSE_MEDIA_UNREADABLE',`MEDIA_URL_UNSUPPORTED: Liên kết chưa gắn được với đúng ô. Loại liên kết: ${[...new Set(state.unsupported.map(item=>item.scheme+' ('+item.locationClass+', '+item.element+')'))].join(', ')}. Không tự tạo lại yêu cầu.`,502);
        await pause(this.pollMs);
      }
      throw fail('MUSE_TIMEOUT','Đã hết thời gian của lượt tạo, trước giới hạn 250 giây. Tool không tự tạo lại yêu cầu đã gửi.',504);
    }catch(error){rejectPending(error)}finally{
      release?.();
      for(const row of rows){if(!row.done)row.reject(row.signal.aborted?row.signal.reason:fail('MUSE_BATCH_INCOMPLETE','Chưa nhận được kết quả của ô.'));if(sent)this.sharedSignals.delete(row.fileToken)}
      if(!this.sharedSignals.size)this.sharedStopPromise=null;
    }
  }
  async sendTurn(options){return options.sharedConversation?this.chatBatches.add(options):this.sendOneTurn(options)}
  async recoverMedia(data,signal){
    this.requireSingleAccount(data.accountId);signal.throwIfAborted();
    const key=randomUUID(),progress={batchId:data.batchId||null,sceneId:data.sceneId,output:data.output,phase:'recovering',submitted:false,active:true,startedAt:Date.now()};
    this.workerStages.set(key,progress);let release;
    try{
      release=await this.acquireComposer(signal);await this.open(data.accountId);await this.refreshActive({includeDetails:false});signal.throwIfAborted();
      if(!this.account(data.accountId).authenticated)throw fail('MUSE_LOGIN_REQUIRED','Đăng nhập đúng tài khoản Muse trước khi nhận lại tệp.',401);
      let saved,frame;
      for(const candidate of await this.composerFrames(this.active.page)){
        const found=await candidate.evaluate(findSavedBatch,{sceneId:data.sceneId,prompt:data.prompt,output:data.output});
        if(found){saved=found;frame=candidate;break}
      }
      if(!saved)throw fail('MUSE_RECOVER_HISTORY_MISSING','Chưa thấy lượt gộp có đúng số ô và toàn bộ prompt này. Mở đúng cuộc trò chuyện trong Đăng nhập Muse trong tool, mở rộng tin nhắn prompt nếu đang thu gọn rồi Nhận lại. Chưa gửi lệnh tạo mới.',404);
      const baseline=await frame.evaluate(inspectBatchDOM,{marker:saved.marker,rows:saved.rows,captureOnly:true,beforeMarker:true,output:data.output});
      const deadline=Date.now()+Math.min(15000,this.timeoutMs);let state;
      do{
        signal.throwIfAborted();
        state=await frame.evaluate(inspectBatchDOM,{marker:saved.marker,rows:saved.rows,baseline:baseline.keys,baselineTexts:baseline.texts,acknowledged:true,output:data.output,allowScopedLabels:true});
        progress.observation={checkedAt:new Date().toISOString(),messageAcknowledged:true,assistantReplies:state.replyCount,visibleVideos:data.output==='video'?state.media.length:0,visibleImages:data.output==='image'?state.media.length:0,matchedMedia:Boolean(state.matches[saved.fileToken]),matchedCount:Object.keys(state.matches).length,unmatchedCount:state.unclaimed,captionLinked:state.captionLinked,unsupportedMedia:state.unsupported.map(item=>({scheme:item.scheme,locationClass:item.locationClass,element:item.element,sceneId:null})),replyLayout:state.replyLayout,streaming:state.streaming,replyScope:'saved-batch',reply:replyPreview(state.text),batchSize:saved.rows.length,messagesSent:0,recoveryOnly:true,waitLimitSeconds:250};
        if(!state.matches[saved.fileToken]){const withinTurn=await frame.evaluate(inspectBatchDOM,{marker:saved.marker,rows:saved.rows,baseline:baseline.keys,baselineTexts:baseline.texts,acknowledged:true,output:data.output,allowScopedLabels:true,turnOnly:true});if(withinTurn.matches[saved.fileToken])state=withinTurn;}
        const media=state.matches[saved.fileToken];
        if(!media){const problem=replyProblem(state.rowTexts[saved.fileToken]);if(problem)throw fail(problem,replyPreview(state.rowTexts[saved.fileToken]),422);}
        if(media){progress.phase='downloading';let lastError;const candidates=[media,...state.media.filter(item=>item.owner===saved.fileToken&&item.key!==media.key)];for(const candidate of candidates){try{const result=await this.downloadMedia(frame,{...candidate,tryMissingControl:true},data.output,signal);progress.phase='done';return result}catch(error){if(signal.aborted)throw error;lastError=error}}throw lastError;}
        await pause(Math.min(300,this.pollMs),signal);
      }while(Date.now()<deadline);
      throw fail('MUSE_RECOVER_NO_MATCH',`Lượt đã tạo có ${state?.media.length||0} nguồn media, chưa đối chiếu được tệp cho ô ${data.sceneId}. Chưa gửi prompt hoặc tạo thêm tệp.`,409);
    }catch(error){progress.phase=signal.aborted?'cancelled':'error';throw error}
    finally{progress.active=false;release?.();}
  }
  async sendOneTurn({ page, prompt, image, output, signal, onSubmit, beforeSubmit, onStage = () => {},onObservation=()=>{},sharedConversation=false,trackAtStart=false }) {
    let releaseComposer=sharedConversation?await this.acquireComposer(signal):null;
    try{
    if(sharedConversation&&this.parallelStrategy!=='shared-conversation')throw fail('MUSE_PARALLEL_UNVERIFIED','Đã chuyển về tuần tự trước khi gửi ô này.',409);
    let editor = await this.findComposer(page) || await this.initialComposer(page) || await this.waitForComposer(page);
    if ((await editor.innerText().catch(() => '')).trim() || (await editor.inputValue().catch(() => '')).trim()) throw fail('MUSE_DRAFT_EXISTS', 'Ô soạn Muse đang có nội dung chưa gửi. Gửi hoặc xóa bản nháp đó trước; tool không ghi đè.', 409);
    if (await editor.locator('xpath=ancestor::*[@data-hatch-composer-root or self::form][1]').locator('img[src^="blob:"]:not([data-message-item] *)').count()) throw fail('MUSE_DRAFT_EXISTS', 'Ô soạn Muse đang có ảnh chưa gửi. Xử lý bản nháp đó trước; tool không gửi kèm ảnh cũ.', 409);
    if (image) await this.attach(page, image);
    signal.throwIfAborted();
    const marker = `studio-request-${randomUUID()}`;
    const fileToken='MUSE_'+marker.slice('studio-request-'.length).replaceAll('-','');
    const delivery=sharedConversation?`\nTracking label for this task: ${fileToken}. Generate the media now and return the native image/video attachment. Include this label in the same reply as its result. If the service provides a real download link, label that link ${fileToken} while preserving its actual working URL and filename. Do not invent file paths or delay generation to rename a file. Prefix any error for this task with ${fileToken}. Other requests are independent; start this task without waiting for their results.`:'';
    const requestTag=`[Request marker: ${marker}. Do not include this marker in your reply.]`;
    const message=sharedConversation?`[${fileToken}]\n${requestTag}\n${prompt}${delivery}`:trackAtStart?`${requestTag}\n${prompt}`:`${prompt}\n\n${requestTag}`;
    const earlierAssistantIds=await page.evaluate(()=>[...document.querySelectorAll('[data-message-item][data-message-role="assistant"]')].map(node=>{node.dataset.museStudioObservationId||=crypto.randomUUID();return node.dataset.museStudioObservationId}));
    editor = await this.writeMessage(page, message, signal);
    signal.throwIfAborted();
    if(beforeSubmit){onStage('waiting-cohort');await beforeSubmit();signal.throwIfAborted();}
    onSubmit();
    this.inFlightMarkers.add(marker);if(sharedConversation)this.sharedSignals.set(marker,signal);
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
        const result = await page.evaluate(({ messages, stop, notice, marker, otherMarkers,sharedConversation,fileToken,output,acknowledged,earlierAssistantIds }) => {
          const visible = el => Boolean(el && el.getClientRects().length);
          const prior=new Set(earlierAssistantIds);
          const isNew=node=>{node.dataset.museStudioObservationId||=crypto.randomUUID();return !prior.has(node.dataset.museStudioObservationId)};
          const nodes = Array.from(document.querySelectorAll(messages));
          const anchor = nodes.findLastIndex(node => node.getAttribute('data-message-role') === 'user' && (node.textContent.includes(marker)||(sharedConversation&&node.textContent.trimStart().startsWith('['+fileToken+']'))));
          const nextUser = anchor < 0 ? -1 : nodes.findIndex((node, index) => index > anchor && node.getAttribute('data-message-role') === 'user');
          const replies = (sharedConversation&&acknowledged?nodes:anchor<0?[]:nodes.slice(anchor+1,sharedConversation?undefined:nextUser<0?undefined:nextUser)).filter(node=>node.getAttribute('data-message-role')==='assistant'&&isNew(node));
          const shared = nodes.some(node => node.getAttribute('data-message-role') === 'user' && otherMarkers.some(other => node.textContent.includes(other)));
          // A generated player often uses preload=none: currentSrc/readyState
          // stay empty until a human presses Play. Read the file source instead
          // of waiting for decoder metadata or for the remaining caption stream.
          const nativeURL=value=>{try{const url=new URL(value,location.href);return !url.username&&!url.password&&(['attachment:','artifact:'].includes(url.protocol)||(url.protocol==='sandbox:'&&Boolean(url.pathname||url.hostname)))}catch{return false}};
          const clickSafe=value=>{try{const url=new URL(value,location.href);return !url.username&&!url.password&&!/^(?:javascript|vbscript|mailto|tel|sms|intent|shell|ms-[a-z-]+):$/i.test(url.protocol)}catch{return false}};
          const linkSource=el=>{const url=new URL(el.href,location.href),nativeControl=clickSafe(el.href),direct=['https:','blob:','data:'].includes(url.protocol)||(url.protocol==='http:'&&url.hostname==='127.0.0.1');const nativeDownload=nativeControl&&(nativeURL(el.href)||!direct);if(nativeControl)el.dataset.museStudioFileId||=crypto.randomUUID();return {src:el.href,width:0,height:0,nativeDownload,nativeControl,nativeId:nativeControl?el.dataset.museStudioFileId:undefined}};
          const links=replies.flatMap(node=>Array.from(node.querySelectorAll('a[href]'))).filter(el=>/\.(mp4|webm|mov)(?:$|[?#])/i.test(el.href)||/\.(mp4|webm|mov)$/i.test(el.download||'')||/^video\//i.test(el.type||'')).map(linkSource);
          const players=replies.flatMap(node=>Array.from(node.querySelectorAll('video'))).map(el=>({src:el.currentSrc||el.getAttribute('src')||el.querySelector('source[src]')?.src,duration:Number.isFinite(el.duration)?el.duration:undefined,width:el.videoWidth,height:el.videoHeight})).filter(el=>el.src);
          const videos=[...links,...players];
          const images = replies.flatMap(node => Array.from(node.querySelectorAll('img'))).filter(el => !el.closest('video') && (el.getAttribute('data-src')||el.getAttribute('data-original')||!el.complete||!el.naturalWidth||(el.naturalWidth>=128&&el.naturalHeight>=128))).map(el => ({ src: el.getAttribute('data-src')||el.getAttribute('data-original')||el.currentSrc||el.getAttribute('src'), width: el.naturalWidth, height: el.naturalHeight })).filter(el=>el.src&&!/^(?:data:image\/svg|.*\.svg(?:[?#]|$))/i.test(el.src));
          if(output==='image')images.push(...replies.flatMap(node=>Array.from(node.querySelectorAll('a[href]'))).filter(el=>/\.(png|jpe?g|webp|avif|gif)(?:$|[?#])/i.test(el.href)||/^image\//i.test(el.type||'')).map(linkSource));
          const mediaURL=(value)=>{try{const url=new URL(value,location.href);return ['https:','blob:','data:'].includes(url.protocol)||(url.protocol==='http:'&&url.hostname==='127.0.0.1')}catch{return false}};
          const attributedLinks=sharedConversation?replies.flatMap(node=>Array.from(node.querySelectorAll('a[href]'))).filter(el=>[el.textContent,el.getAttribute('download'),el.href].some(value=>value?.includes(fileToken))):[];
          const namedLinks=attributedLinks.filter(el=>clickSafe(el.href));
          const unsupportedMediaLinks=attributedLinks.filter(el=>!clickSafe(el.href)).length;
          const namedElements=sharedConversation?replies.flatMap(node=>Array.from(node.querySelectorAll(output==='video'?'video':'img'))).filter(el=>{if([el.getAttribute('alt'),el.getAttribute('aria-label'),el.getAttribute('src'),el.querySelector('source[src]')?.src].some(value=>value?.includes(fileToken)))return true;const container=el.closest('figure')||el.closest('[data-message-item]');const tokens=new Set(container?.textContent.match(/\bMUSE_[a-f0-9]{32}\b/g)||[]);return tokens.size===1&&tokens.has(fileToken)&&container.querySelectorAll(output==='video'?'video':'img').length===1;}):[];
          const namedSources=namedElements.map(el=>({src:el.currentSrc||el.getAttribute('src')||el.querySelector('source[src]')?.src,width:el.videoWidth||el.naturalWidth||0,height:el.videoHeight||el.naturalHeight||0})).filter(media=>media.src&&mediaURL(media.src));
          const buttonSources=replies.flatMap(node=>[...node.querySelectorAll('button,[role="button"]')]).filter(node=>{const name=[node.getAttribute('aria-label'),node.getAttribute('title'),node.innerText].join(' ');return /\bdownload\b|\bsave (?:image|video|file)\b|tải (?:xuống|về|ảnh|video|tệp|file)/i.test(name)&&!/\b(?:all|zip|generate|create)\b|tất cả|tạo (?:ảnh|video)/i.test(name)}).map(node=>{node.dataset.museStudioFileId||=crypto.randomUUID();const name=[node.getAttribute('aria-label'),node.getAttribute('title'),node.innerText].join(' '),kind=/\bvideo\b/i.test(name)?'video':/\bimage\b|ảnh/i.test(name)?'image':output;return {src:'muse-file-control:'+node.dataset.museStudioFileId,width:0,height:0,nativeDownload:true,nativeControl:true,nativeButton:true,nativeId:node.dataset.museStudioFileId,kind,owned:node.closest('[data-message-item]')?.textContent.includes(fileToken)}});
          images.push(...buttonSources.filter(item=>item.kind==='image'));videos.push(...buttonSources.filter(item=>item.kind==='video'));
          const namedMedia=namedSources[0]||(namedLinks.length?linkSource(namedLinks[0]):buttonSources.find(item=>item.kind===output&&item.owned)||null);
          const error = replies.flatMap(node => Array.from(node.querySelectorAll(notice))).find(el=>visible(el)&&(!sharedConversation||el.closest('[data-message-item]')?.textContent.includes(fileToken)));
          const ownedText=sharedConversation?replies.filter(node=>{const tokens=new Set(node.textContent.match(/\bMUSE_[a-f0-9]{32}\b/g)||[]);return tokens.size===1&&tokens.has(fileToken)}).map(node=>node.innerText).join('\n\n'):'';
          const freshReplies=replies.filter(isNew);
          const contextText=freshReplies.filter(node=>!Array.from(node.textContent.matchAll(/\bMUSE_[a-f0-9]{32}\b/g)).some(match=>match[0]!==fileToken)).map(node=>node.innerText).join('\n\n').trim();
          return {unsupportedMediaLinks,contextText,replyCount:freshReplies.length,ownedText,namedMedia,anchored: anchor >= 0, shared, interrupted: nextUser >= 0, text: replies.map(node => node.innerText).join('\n\n').trim(), videos, images,
            streaming: visible(document.querySelector(stop)), error: error?.innerText || '' };
        }, { messages: MESSAGES, stop: STOP, notice: NOTICE, marker, otherMarkers: [...this.inFlightMarkers].filter(other => other !== marker),sharedConversation,fileToken,output,acknowledged,earlierAssistantIds });
        if (!sharedConversation&&(result.shared || (result.interrupted && !result.images.length && !result.videos.length && !result.text))) {
          for (const active of this.inFlightMarkers) this.unsafeMarkers.add(active);
          this.maxConcurrency = 1;
          throw fail('MUSE_SHARED_CONVERSATION', 'Một hội thoại nhận nhiều yêu cầu xen kẽ. Tool dừng để tránh lấy nhầm ảnh; hãy chuẩn bị lại các ô trước khi chạy tiếp. Không tự gửi lại.', 409);
        }
        if(result.error){const capacity=/concurren|at (?:the same|a) time|already (?:generating|processing)|too many (?:active|parallel|simultaneous)|tác vụ.{0,40}đồng thời/i.test(result.error);const error=fail(capacity?'MUSE_PARALLEL_LIMIT':'MUSE_GENERATION_ERROR',result.error);if(capacity)error.safeSerialRetry=true;throw error;}
        if ((result.anchored||(sharedConversation&&result.namedMedia)) && !acknowledged) { acknowledged = true; onStage('submitted');releaseComposer?.();releaseComposer=null; }
        if (!result.anchored && !acknowledged && Date.now() >= acknowledgementDeadline) throw fail('MUSE_SUBMIT_NOT_ACKNOWLEDGED', 'Muse chưa xác nhận đã nhận prompt sau thao tác gửi. Tool không tự gửi lại. Mở cuộc trò chuyện kiểm tra trước khi thử lại để tránh tạo trùng.', 504);
        onObservation({checkedAt:new Date().toISOString(),messageAcknowledged:acknowledged,assistantReplies:result.replyCount,visibleVideos:result.videos.length,visibleImages:result.images.length,matchedMedia:sharedConversation?Boolean(result.namedMedia):output==='video'?result.videos.length>0:output==='image'?result.images.length>0:false,streaming:result.streaming,replyScope:result.ownedText?'scene':'conversation',reply:replyPreview(result.ownedText||result.contextText)});
        if(acknowledged&&result.contextText&&!result.namedMedia)onStage('reply-received');
        if (result.text !== lastText) { lastText = result.text; stableSince = Date.now(); }
        if (output === 'text' && result.anchored && result.text && !result.streaming && Date.now() - stableSince >= this.quietMs) return { text: result.text };
        const media = sharedConversation?result.namedMedia:output === 'video' ? result.videos[0] : output === 'image' ? result.images[0] : null;
        if (media && (sharedConversation||!result.streaming||output==='video')) {
          onStage('downloading');
          return {...await this.downloadMedia(page,media,output,signal),captionPending:!sharedConversation&&output==='video'&&result.streaming};
        }
        if(sharedConversation&&!media&&!result.streaming&&result.unsupportedMediaLinks&&Date.now()-stableSince>=this.replyQuietMs)throw fail('MUSE_MEDIA_UNREADABLE','MEDIA_URL_UNSUPPORTED: Muse trả liên kết không tải trực tiếp được và chưa có ảnh/video thật thay thế. Xem phản hồi Muse; tool không tự tạo lại yêu cầu.',502);
        if(output!=='text'&&!result.streaming&&!media&&!result.videos.length&&!result.images.length&&Date.now()-stableSince>=this.replyQuietMs){
          const reply=result.ownedText||result.contextText;const problem=replyProblem(reply);
          if(problem)throw fail(problem,`Muse đã trả lời nhưng chưa tạo ${output==='video'?'video':'ảnh'}. Phản hồi ${result.ownedText?'của cảnh':'trong cuộc trò chuyện'}: ${replyPreview(reply)}`,422);
        }
        if (!sharedConversation&&output !== 'text' && result.text && !media && !result.streaming && Date.now() - stableSince > 20000) throw fail(output === 'image' ? 'MUSE_NO_IMAGE' : 'MUSE_NO_VIDEO', `Muse chưa trả ${output === 'image' ? 'ảnh' : 'video'} cho yêu cầu này. Phản hồi: ${result.text.slice(0, 1000)}`);
      }
      throw fail('MUSE_TIMEOUT', 'Hết thời gian chờ Muse. Kiểm tra cửa sổ Muse trước khi thử lại để tránh tạo trùng hoặc tính phí hai lần.', 504);
    } catch (error) {
      if (signal.aborted) {
        if(sharedConversation){onStage('cancelled-provider');await this.finishCancelledShared(page,fileToken,deadline);throw signal.reason;}
        // A hidden worker still has a live DOM. Dispatch Stop there and give its
        // request time to finish before disposing the view, which aborts fetches.
        await page.locator(STOP).first().evaluate(button => button.click(), undefined, { timeout: 3000 }).catch(() => {});
        // Let the website dispatch its Stop request before tearing down several
        // views together. A previously idle frame may report networkidle before
        // the click's new fetch has entered Playwright's network bookkeeping.
        await pause(200);
        await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
        throw signal.reason;
      }
      throw error;
    } finally { this.inFlightMarkers.delete(marker); this.unsafeMarkers.delete(marker);if(sharedConversation){this.sharedSignals.delete(marker);if(!this.sharedSignals.size)this.sharedStopPromise=null;} }
    }finally{releaseComposer?.();}
  }
  async finishCancelledShared(page,fileToken,deadline){
    while(Date.now()<deadline&&this.active&&!this.active.page.isClosed()){
      if([...this.sharedSignals.values()].every(signal=>signal.aborted)){
        if(!this.sharedStopPromise)this.sharedStopPromise=(async()=>{await page.locator(STOP).first().evaluate(button=>button.click(),undefined,{timeout:3000}).catch(()=>{});await pause(200)})();
        await this.sharedStopPromise;return;
      }
      const completed=await page.evaluate(token=>[...document.querySelectorAll('[data-message-item][data-message-role="assistant"]')].some(node=>[...node.querySelectorAll('a[href],img,video')].some(el=>[el.textContent,el.getAttribute('alt'),el.getAttribute('aria-label'),el.getAttribute('href'),el.getAttribute('src'),el.getAttribute('download')].some(value=>value?.includes(token)))),fileToken).catch(()=>false);
      if(completed)return;await pause(100);
    }
  }
  async downloadMedia(page,media,output,signal){
    const work=value=>mediaQueue.run(()=>this.downloadMediaNow(page,value,output,signal),signal);
    if(media.nativeDownload)return this.nativeFileQueue.run(()=>work(media),signal);
    try{return await work(media)}catch(error){
      const missing=/MEDIA_HTTP_404|MEDIA_EMPTY/.test(error.message);if(signal.aborted||!media.nativeId||!media.nativeControl||(missing&&!media.tryMissingControl))throw error;
      // Release the shared transfer slot before waiting for this account's
      // download control. Other accounts keep their own download capacity.
      try{return await this.nativeFileQueue.run(()=>work({...media,nativeDownload:true}),signal)}catch(nativeError){if(missing&&!signal.aborted)throw error;throw nativeError}
    }
  }
  async downloadMediaNow(page,media,output,signal){
          const downloadKey=`__studio_download_${randomUUID().replaceAll('-','')}`;
          signal.throwIfAborted();
          const abortDownload=()=>{void page.evaluate(key=>{if(globalThis[key]?.abort)globalThis[key].abort();else globalThis[key]='aborted'},downloadKey).catch(()=>{})};
          signal.addEventListener('abort',abortDownload,{once:true});
          try{
          const read=async nativeMedia=>await page.evaluate(async ({ src, output,downloadKey,nativeMedia }) => {
            const url = new URL(src, location.href);
            if (!nativeMedia && !['https:', 'blob:', 'data:'].includes(url.protocol) && !(url.protocol === 'http:' && url.hostname === '127.0.0.1')) throw new Error('MEDIA_URL_UNSUPPORTED');
            const cancelled=globalThis[downloadKey]==='aborted';const control=new AbortController();globalThis[downloadKey]=control;if(cancelled)control.abort();
            const timer=setTimeout(()=>control.abort(),120000);
            try{
            let blob;
            if(nativeMedia){const bytes=Uint8Array.from(atob(nativeMedia.base64),char=>char.charCodeAt(0));blob=new Blob([bytes],{type:nativeMedia.mimeType})}
            else{let response;try{response=await fetch(url.href,{signal:control.signal,credentials:'same-origin'})}catch{throw Error('MEDIA_FETCH_FAILED')}
              if(!response.ok)throw Error('MEDIA_HTTP_'+response.status);if(/^(?:text\/html|application\/json)(?:;|$)/i.test(response.headers.get('content-type')||''))throw Error('MEDIA_RESPONSE_NOT_MEDIA');blob=await response.blob();}
            if(!blob.size)throw Error('MEDIA_EMPTY');if(blob.size>100*1024*1024)throw Error('MEDIA_TOO_LARGE');
            let fingerprint, width, height,duration;
            if(output==='video'){
              const head=new Uint8Array(await blob.slice(0,16).arrayBuffer());
              if([0x1a,0x45,0xdf,0xa3].every((value,index)=>head[index]===value))blob=new Blob([blob],{type:'video/webm'});
              else{
                let offset=0,moov=false,mdat=false;
                for(let boxes=0;offset+8<=blob.size&&boxes<256;boxes++){
                  const bytes=new Uint8Array(await blob.slice(offset,offset+16).arrayBuffer());const view=new DataView(bytes.buffer);let size=view.getUint32(0),header=8;const type=String.fromCharCode(...bytes.slice(4,8));
                  if(size===1){if(bytes.length<16)throw new Error('Incomplete video header');const large=view.getBigUint64(8);if(large>BigInt(Number.MAX_SAFE_INTEGER))throw new Error('Invalid video size');size=Number(large);header=16}else if(size===0)size=blob.size-offset;
                  if(size<header||offset+size>blob.size)throw new Error('Incomplete video file');moov||=type==='moov';mdat||=type==='mdat';
                  if(type==='moov'){
                    const movie=new Uint8Array(await blob.slice(offset+header,offset+size).arrayBuffer());const details=new DataView(movie.buffer);
                    const walk=(start,end,depth=0)=>{for(let at=start,boxes=0;at+8<=end&&boxes<256;boxes++){
                      const length=details.getUint32(at);if(length<8||at+length>end)return;const kind=String.fromCharCode(...movie.slice(at+4,at+8));const data=at+8;
                      if(kind==='mvhd'&&length>=32){const version=movie[data],scaleOffset=data+(version===1?20:12),durationOffset=scaleOffset+4;if(durationOffset+(version===1?8:4)<=at+length){const scale=details.getUint32(scaleOffset);const ticks=version===1?Number(details.getBigUint64(durationOffset)):details.getUint32(durationOffset);if(scale&&ticks>0)duration=ticks/scale}}
                      if(kind==='tkhd'&&length>=84){const w=details.getUint32(at+length-8)/65536,h=details.getUint32(at+length-4)/65536;if(w>0&&h>0&&(!width||w*h>width*height)){width=Math.round(w);height=Math.round(h)}}
                      if(depth<5&&['trak','mdia'].includes(kind))walk(data,at+length,depth+1);at+=length;
                    }};walk(0,movie.length);
                  }
                  offset+=size;
                }
                if(!moov||!mdat)throw new Error('Not a complete MP4/MOV file');blob=new Blob([blob],{type:blob.type==='video/quicktime'?'video/quicktime':'video/mp4'});
              }
            }
            if (output === 'image') {
              const bitmap = await createImageBitmap(blob);
              try {
                width = bitmap.width; height = bitmap.height;
                if (width<128 || height<128 || width * height > 33554432) throw new Error('Image dimensions exceed limit');
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
            return await new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve({ base64: String(reader.result).split(',')[1], mimeType: blob.type, fingerprint, width, height,duration }); reader.onerror = reject; reader.readAsDataURL(blob); });
            }finally{clearTimeout(timer);delete globalThis[downloadKey]}
          }, { src: media.src, output,downloadKey,nativeMedia });
          let base64;try{base64=media.nativeDownload?await read(await (this.active?.readAttachment?this.active.readAttachment(page,media,signal):readPageAttachment(page,media,signal,{timeoutMs:Math.min(15000,Math.max(500,this.timeoutMs-1000))}))):await read(null)}catch(error){
            if(signal.aborted)throw signal.reason;
            try{if(!this.active?.readMedia||!/MEDIA_FETCH_FAILED|MEDIA_HTTP_40[13]/.test(error.message))throw error;const nativeMedia=await this.active.readMedia(new URL(media.src,page.url()).href,signal);signal.throwIfAborted();base64=await read(nativeMedia)}catch(cause){
              if(signal.aborted)throw signal.reason;
              throw fail('MUSE_MEDIA_UNREADABLE',`Không tải hoặc giải mã được tệp Muse. Chi tiết: ${replyPreview(cause.message).slice(0,500)}. Tool không tạo lại yêu cầu đã gửi.`,502);
            }
          }
          signal.throwIfAborted();
          return { ...base64,captionPending:false, mimeType: base64.mimeType?.startsWith(`${output}/`) ? base64.mimeType : output === 'image' ? 'image/png' : 'video/mp4', metadata: { ...(output === 'video' ? { duration: base64.duration||media.duration } : {}), width: base64.width || media.width, height: base64.height || media.height } };
          }finally{signal.removeEventListener('abort',abortDownload);void page.evaluate(key=>{delete globalThis[key]},downloadKey).catch(()=>{})}
  }
  async generateVideo(data, signal) {
    const referenceInstruction = data.sourceMode === 'image' ? 'Animate the attached image as the starting frame.' : data.referenceImage ? 'Use the attached image as a character reference, not as an unrelated example.' : 'Create the video from the text prompt.';
    const prompt = `Use your video-generation tool to create exactly one new video, not a link to an existing example. Requested model: ${data.modelDisplayName}. Requested duration: ${data.durationSeconds} seconds, aspect ratio: ${data.aspectRatio}, resolution: ${data.resolution}. Start the available video-generation tool now. These are target settings: if an exact model name or parameter is unavailable, use supported generation settings and report the actual settings instead of stopping at a text-only explanation. Do not invent model options, return only a written plan, or ask for confirmation to start this requested generation. If no video generation is available, state the concrete reason. ${referenceInstruction} ${data.characterLock !== false ? 'Preserve the referenced character identity and appearance across scenes.' : 'Follow this scene prompt independently; character consistency is not requested.'}\nScene:\n${data.prompt}`;
    return this.turn({ accountId: data.accountId, prompt, image: data.referenceImage, video: true, signal, batchId: data.batchId, sceneId: data.sceneId, submissionGroup:data.submissionGroup, singleLane: data.singleLane });
  }
  async generateImage(data, signal) {
    const longEdge = data.resolution === '4k' ? 3840 : 2560;
    const dimensions = data.aspectRatio === '9:16' ? `${Math.round(longEdge * 9 / 16)}x${longEdge}` : `${longEdge}x${Math.round(longEdge * 9 / 16)}`;
    const useReference = data.characterLock !== false && data.referenceImage;
    const prompt = `Use your image-generation tool to create exactly one new image for this scene. Requested native output: ${data.resolution.toUpperCase()} (${dimensions} pixels), aspect ratio ${data.aspectRatio}. Return the generated image, not a stock image or an old response. Do not claim a higher resolution than the image actually has. ${useReference ? 'Use the attached portrait as a character reference; preserve identity, face and appearance consistently.' : data.characterLock !== false ? 'Follow the character description in this prompt. No portrait is attached; cross-scene identity is not guaranteed without a reference.' : 'Follow this prompt independently. Do not reuse characters or appearance from earlier scenes unless the prompt explicitly requests them.'}\nScene:\n${data.prompt}`;
    return this.turn({ accountId: data.accountId, prompt, image: useReference || undefined, output: 'image', signal, batchId: data.batchId, sceneId: data.sceneId, submissionGroup:data.submissionGroup, singleLane: data.singleLane });
  }
  async generateText(data, signal) { return this.turn({ accountId: data.accountId, prompt: data.prompt, video: false, signal, batchId: data.batchId, sceneId: data.sceneId, submissionGroup:data.submissionGroup, singleLane: data.singleLane }); }
}
