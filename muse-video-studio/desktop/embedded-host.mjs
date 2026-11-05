import { WebContentsView } from 'electron';
import { chromium } from 'playwright-core';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { randomUUID } from 'node:crypto';

export const remotePreferences = { partition: 'persist:muse', sandbox: true, contextIsolation: true, nodeIntegration: false, webSecurity: true, backgroundThrottling: false };

export class EmbeddedMuseHost {
  constructor({ window, userData, serviceURL }) {
    this.window = window;
    this.userData = userData;
    this.serviceURL = serviceURL;
    this.views = new Map();
    this.login = null;
    this.browser = null;
  }
  allowNavigation(url) {
    // OAuth/email clients commonly open an empty window and navigate it later.
    // It keeps the same sandboxed Muse partition and never receives a preload.
    if (!url || url === 'about:blank') return true;
    try { const target = new URL(url); return target.protocol === 'https:' || (target.origin === new URL(this.serviceURL).origin && target.hostname === '127.0.0.1'); }
    catch { return false; }
  }
  secure(contents) {
    contents.on('will-navigate', (event, url) => { if (!this.allowNavigation(url)) event.preventDefault(); });
    contents.setWindowOpenHandler(({ url }) => this.allowNavigation(url) ? { action: 'allow', overrideBrowserWindowOptions: { parent: this.window, width: 760, height: 800, autoHideMenuBar: true, webPreferences: remotePreferences } } : { action: 'deny' });
    contents.on('did-create-window', child => this.secure(child.webContents));
    contents.setAudioMuted(true);
  }
  async attach() {
    if (this.browser?.isConnected()) return this.browser;
    let port;
    for (let attempt = 0; attempt < 100; attempt++) {
      try { port = Number((await readFile(path.join(this.userData, 'DevToolsActivePort'), 'utf8')).split('\n')[0]); if (port > 0) break; } catch {}
      await new Promise(resolve => setTimeout(resolve, 50));
    }
    if (!port) throw new Error('DESKTOP_CONNECTION_FAILED: Không kết nối được trình đăng nhập tích hợp. Khởi động lại tool.');
    this.browser = await chromium.connectOverCDP(`http://127.0.0.1:${port}`, { timeout: 15000 });
    return this.browser;
  }
  async createView({ worker = false } = {}) {
    const browser = await this.attach();
    const view = new WebContentsView({ webPreferences: remotePreferences });
    this.secure(view.webContents);
    this.window.contentView.addChildView(view);
    view.setVisible(false);
    const marker = `about:blank#studio-${randomUUID()}`;
    try {
      await view.webContents.loadURL(marker);
      let page;
      for (let attempt = 0; attempt < 100; attempt++) {
        page = browser.contexts().flatMap(context => context.pages()).find(candidate => candidate.url() === marker);
        if (page) break;
        await new Promise(resolve => setTimeout(resolve, 30));
      }
      if (!page) throw new Error('DESKTOP_VIEW_FAILED: Không khởi tạo được luồng Muse tích hợp.');
      // Verification also opens the login view while hidden, so it needs layout
      // metrics just like workers, even before the user displays the view.
      const [width, height] = this.window.getContentSize();
      const viewport = worker ? { width: 1280, height: 900 } : { width, height: Math.max(1, height - 54) };
      await page.setViewportSize(viewport);
      this.views.set(page, view);
      this.layout();
      return { page, view, viewport };
    } catch (error) { this.window.contentView.removeChildView(view); view.webContents.close(); throw error; }
  }
  layout() {
    if (this.window.isDestroyed()) return;
    const [width, height] = this.window.getContentSize();
    for (const view of this.views.values()) view.setBounds({ x: 0, y: 54, width, height: Math.max(1, height - 54) });
    const viewport = { width, height: Math.max(1, height - 54) };
    if (this.login && (this.login.viewport.width !== viewport.width || this.login.viewport.height !== viewport.height)) {
      this.login.viewport = viewport;
      void this.login.page.setViewportSize(viewport).catch(() => {});
    }
  }
  showLogin() {
    if (!this.login) return;
    this.window.contentView.addChildView(this.login.view);
    this.login.view.setVisible(true);
    this.layout();
    this.login.view.webContents.focus();
    this.window.webContents.send('studio:view-changed', 'muse');
  }
  hideLogin() {
    this.login?.view.setVisible(false);
    this.window.webContents.send('studio:view-changed', 'studio');
  }
  async removePage(page) {
    const view = this.views.get(page);
    this.views.delete(page);
    if (view && !view.webContents.isDestroyed()) {
      if (!this.window.isDestroyed()) this.window.contentView.removeChildView(view);
      view.webContents.close();
    }
  }
  async openSession() {
    this.login = await this.createView();
    const login = this.login;
    return {
      context: login.page.context(), page: login.page,
      showLogin: () => this.showLogin(),
      createWorkerPage: async () => (await this.createView({ worker: true })).page,
      destroyWorkerPage: page => this.removePage(page),
      close: async () => {
        await Promise.all([...this.views.keys()].map(page => this.removePage(page)));
        this.login = null;
        this.hideLogin();
      },
    };
  }
  async close() {
    await Promise.all([...this.views.keys()].map(page => this.removePage(page)));
    this.login = null;
    await this.browser?.close();
    this.browser = null;
  }
}
