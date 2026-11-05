import { app, BrowserWindow, WebContentsView, ipcMain, dialog, session } from 'electron';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { startStudioServer } from '../server.mjs';
import { MuseBrowser } from '../muse-browser.mjs';
import { EmbeddedMuseHost } from './embedded-host.mjs';

const directory = path.dirname(fileURLToPath(import.meta.url));
const root = path.dirname(directory);
const version = JSON.parse(readFileSync(path.join(root, 'package.json'), 'utf8')).version;
const userData = path.resolve(process.env.MUSE_DESKTOP_DATA || path.join(root, '.data', 'muse-desktop'));
mkdirSync(userData, { recursive: true, mode: 0o700 });
const portFile = path.join(userData, 'studio-port');
function savedStudioPort() {
  try { const port = Number(readFileSync(portFile, 'utf8')); return Number.isInteger(port) && port >= 1024 && port <= 65535 ? port : 0; }
  catch { return 0; }
}
app.setPath('userData', userData);
app.setName('Muse AI Studio');
app.commandLine.appendSwitch('remote-debugging-port', '0');
app.commandLine.appendSwitch('remote-debugging-address', '127.0.0.1');
app.commandLine.appendSwitch('disable-background-timer-throttling');
let window; let runtime; let host; let closing = false;
const requests = new Map();

if (!app.requestSingleInstanceLock()) app.quit();
else {
  app.on('second-instance', () => { if (window) { if (window.isMinimized()) window.restore(); window.focus(); } });
  app.whenReady().then(start).catch(error => {
    const message = error.code === 'EADDRINUSE' ? 'Cổng tool đang được bản cũ sử dụng. Đóng máy chủ cũ rồi chạy lại start.bat.' : error.message;
    console.error(message);
    dialog.showErrorBox('Không mở được Muse AI Studio', message);
    app.exit(1);
  });
}

async function start() {
  // The fixture URL is accepted only with an explicit test flag and loopback origin.
  const fixture = process.env.MUSE_DESKTOP_TEST === '1' ? process.env.MUSE_FIXTURE_URL : null;
  if (fixture && (new URL(fixture).protocol !== 'http:' || new URL(fixture).hostname !== '127.0.0.1')) throw new Error('Fixture must use local HTTP.');
  const serviceURL = fixture || 'https://muse.ai/';
  const museSession = session.fromPartition('persist:muse');
  museSession.setPermissionRequestHandler((_contents, _permission, callback) => callback(false));
  const proxyServer = process.env.HTTPS_PROXY || process.env.HTTP_PROXY;
  if (proxyServer) await museSession.setProxy({ proxyRules: proxyServer, proxyBypassRules: 'localhost;127.0.0.1' });
  window = new BrowserWindow({ width: 1480, height: 1000, minWidth: 850, minHeight: 650, title: `Muse AI Studio ${version} · 1 tài khoản / 10 cảnh`, autoHideMenuBar: true,
    webPreferences: { preload: path.join(directory, 'preload.cjs'), sandbox: true, contextIsolation: true, nodeIntegration: false } });
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  host = new EmbeddedMuseHost({ window, userData, serviceURL });
  const muse = new MuseBrowser({ profileRoot: userData, accountProfile: userData, serviceURL, maxConcurrency: fixture && process.env.MUSE_TEST_PARALLEL === '1' ? 10 : 1, sessionFactory: () => host.openSession() });
  const rememberPort = app.isPackaged && !process.env.PORT;
  runtime = await startStudioServer({ museDriver: muse, embeddedLogin: true, ...(rememberPort ? { port: savedStudioPort() } : {}) });
  // Keep the localStorage origin stable on later launches of a portable app.
  if (rememberPort) writeFileSync(portFile, new URL(runtime.url).port);
  const studio = new WebContentsView({ webPreferences: { preload: path.join(directory, 'renderer-preload.cjs'), partition: 'persist:studio', sandbox: true, contextIsolation: true, nodeIntegration: false, webSecurity: true, backgroundThrottling: false } });
  studio.webContents.setWindowOpenHandler(({ url }) => url.startsWith(`blob:${runtime.url}/`) ? {
    action: 'allow', overrideBrowserWindowOptions: { parent: window, width: 1000, height: 750, autoHideMenuBar: true,
      webPreferences: { partition: 'persist:studio', sandbox: true, contextIsolation: true, nodeIntegration: false, webSecurity: true } },
  } : { action: 'deny' });
  studio.webContents.on('did-create-window', child => {
    child.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
    child.webContents.on('will-navigate', event => event.preventDefault());
  });
  studio.webContents.on('will-navigate', (event, url) => { if (new URL(url).origin !== runtime.url) event.preventDefault(); });
  window.contentView.addChildView(studio);
  const layout = () => { const [width, height] = window.getContentSize(); studio.setBounds({ x: 0, y: 54, width, height: Math.max(1, height - 54) }); host.layout(); };
  window.on('resize', layout);
  layout();
  // Main-process requests avoid Chromium's six-connection HTTP/1 limit to localhost.
  // Remote Muse views do not receive this preload or access to these handlers.
  ipcMain.handle('studio:api', async (event, value) => {
    if (event.sender !== studio.webContents || !value || !/^[a-z0-9-]{36}$/i.test(value.id) || !['/api/image', '/api/video', '/api/text'].includes(value.endpoint)) throw new Error('Invalid Studio request');
    if (requests.size >= 10 || requests.has(value.id)) return { ok: false, body: { error: 'MUSE_CONCURRENCY_LIMIT: Đã có 10 luồng đang chạy.' } };
    const body = JSON.stringify(value.data);
    if (Buffer.byteLength(body) > 12 * 1024 * 1024) return { ok: false, body: { error: 'Yêu cầu vượt giới hạn 12 MB.' } };
    const control = new AbortController(); requests.set(value.id, control);
    try {
      const response = await fetch(runtime.url + value.endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body, signal: control.signal });
      return { ok: response.ok, body: await response.json() };
    } catch (error) { return { ok: false, body: { error: control.signal.aborted ? 'ABORTED: Đã dừng luồng.' : error.message } }; }
    finally { requests.delete(value.id); }
  });
  ipcMain.on('studio:cancel', (event, id) => { if (event.sender === studio.webContents) requests.get(id)?.abort(); });
  ipcMain.handle('studio:view', async (event, name) => {
    if (event.sender !== window.webContents) throw new Error('Untrusted sender');
    if (name === 'studio') {
      host.hideLogin(); studio.webContents.focus();
      studio.webContents.send('studio:session-refresh');
    }
    else if (name === 'muse') await muse.connect(1);
    else throw new Error('Unknown view');
  });
  await window.loadFile(path.join(directory, 'shell.html'));
  window.webContents.send('studio:version', version);
  await studio.webContents.loadURL(runtime.url);
  window.on('close', event => { if (!closing) { event.preventDefault(); void shutdown(); } });
  console.log('Muse desktop ready: dang nhap trong tool, mot phien / 10 canh, hang doi an toan.');
}

async function shutdown() {
  closing = true;
  for (const control of requests.values()) control.abort();
  await runtime?.close();
  await host?.close();
  await session.fromPartition('persist:muse').cookies.flushStore();
  app.quit();
}
app.on('window-all-closed', () => app.quit());
app.on('before-quit', event => { if (!closing && runtime) { event.preventDefault(); void shutdown(); } });
