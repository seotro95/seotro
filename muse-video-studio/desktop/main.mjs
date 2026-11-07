import { app, BrowserWindow, WebContentsView, ipcMain, dialog, session, clipboard, shell } from 'electron';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { startStudioServer } from '../server.mjs';
import { MuseBrowser } from '../muse-browser.mjs';
import { MuseAccounts } from '../muse-accounts.mjs';
import { EmbeddedMuseHost } from './embedded-host.mjs';
import { loginRecorder } from './login-diagnostics.mjs';
import { FolderExports } from './folder-export.mjs';
import { AutomationServer } from './automation-server.mjs';
import { randomUUID } from 'node:crypto';

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
let automation; let window; let runtime; let host; let emailWindow; let emailNavigation = false; let closing = false;
const requests = new Map();
const hosts = new Map(); const loginLogs = new Map();
const partitionFor = id => id === 1 ? 'persist:muse' : `persist:muse-${String(id).padStart(2,'0')}`;

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
  window = new BrowserWindow({ width: 1480, height: 1000, minWidth: 850, minHeight: 650, title: `Muse AI Studio ${version} · 1 hoặc 10 tài khoản / 10 cảnh`, autoHideMenuBar: true,
    webPreferences: { preload: path.join(directory, 'preload.cjs'), sandbox: true, contextIsolation: true, nodeIntegration: false } });
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  const muse = await new MuseAccounts({profileRoot:userData,preferredConcurrency:fixture&&process.env.MUSE_TEST_PARALLEL==='1'?10:2,
    createDriver: id => {
      const partition=partitionFor(id); const museSession=session.fromPartition(partition);
      const log=loginRecorder(serviceURL); loginLogs.set(id,log);
      museSession.webRequest.onCompleted(details=>log.completed(details));
      museSession.webRequest.onErrorOccurred(details=>log.failed(details));
      museSession.setPermissionRequestHandler((_contents,_permission,callback)=>callback(false));
      const proxyServer=process.env.HTTPS_PROXY||process.env.HTTP_PROXY;
      const configured=proxyServer?museSession.setProxy({proxyRules:proxyServer,proxyBypassRules:'localhost;127.0.0.1'}):Promise.resolve();
      const ownedHost=new EmbeddedMuseHost({window,userData,serviceURL,partition});hosts.set(id,ownedHost);if(!host)host=ownedHost;
      return new MuseBrowser({profileRoot:userData,accountProfile:id===1?userData:path.join(userData,`account-${id}`),serviceURL,
        maxConcurrency:fixture&&id===1&&process.env.MUSE_TEST_PARALLEL==='1'?10:1,
        sessionFactory:async()=>{await configured;return ownedHost.openSession()}});
    },
    onSelect: id=>{for(const owned of hosts.values())owned.hideLogin();host=hosts.get(id);window.webContents.send('studio:account',id);}
  }).load();
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
  const folderExports = new FolderExports({ userData,
    chooseDirectory: async defaultPath => {
      const result = await dialog.showOpenDialog(window, { title: 'Chọn nơi lưu các bộ ảnh/video', properties: ['openDirectory','createDirectory'], ...(defaultPath ? { defaultPath } : {}) });
      return result.canceled ? null : result.filePaths[0];
    }, openDirectory: directory => shell.openPath(directory) });
  ipcMain.handle('studio:export', async (event, action, data) => {
    if (event.sender !== studio.webContents) throw new Error('Untrusted export sender');
    if (action === 'ensure') return folderExports.ensureDirectory();
    if (action === 'choose') return folderExports.ensureDirectory(true);
    if (action === 'begin') return folderExports.begin(data);
    if (action === 'write') return folderExports.write(data);
    if (action === 'finish') return folderExports.finish(data);
    if (action === 'abort') return folderExports.abort(data);
    throw new Error('Unknown export action');
  });
  let automationReady=false;
  const pendingAutomation=new Map();
  const rejectAutomation=()=>{automationReady=false;for(const task of pendingAutomation.values()){clearTimeout(task.timer);task.reject(Object.assign(new Error('Studio đang tải lại hoặc đóng. Kiểm tra tiến độ trước khi gửi lại bộ.'),{status:503}))}pendingAutomation.clear()};
  studio.webContents.on('did-start-navigation',(_event,_url,_inPlace,isMainFrame)=>{if(isMainFrame)rejectAutomation()});
  studio.webContents.on('destroyed',rejectAutomation);
  const dispatch=(action,data)=>new Promise((resolve,reject)=>{
    if(!automationReady||studio.webContents.isDestroyed())return reject(Object.assign(new Error('Studio chưa sẵn sàng. Mở Studio và đợi tải thư viện.'),{status:503}));
    const id=randomUUID();const timer=setTimeout(()=>{pendingAutomation.delete(id);reject(Object.assign(new Error('Chưa nhận xác nhận từ Studio. Đọc tiến độ trước khi gửi lại; không tự chạy lại.'),{status:504}))},120000);
    pendingAutomation.set(id,{resolve,reject,timer});studio.webContents.send('studio:automation-command',{id,action,data});
  });
  ipcMain.on('studio:automation-ready',(event,ready)=>{if(event.sender===studio.webContents)automationReady=ready===true});
  ipcMain.on('studio:automation-reply',(event,value)=>{
    if(event.sender!==studio.webContents||!value||typeof value.id!=='string')return;
    const task=pendingAutomation.get(value.id);if(!task)return;pendingAutomation.delete(value.id);clearTimeout(task.timer);
    if(value.ok)task.resolve(value.result);else task.reject(Object.assign(new Error(String(value.error||'STUDIO_ERROR').slice(0,1000)),{status:Number.isInteger(value.status)&&value.status>=400&&value.status<=599?value.status:500}));
  });
  automation=await new AutomationServer({userData,dispatch,version}).load();
  ipcMain.handle('studio:automation-control',async(event,action,data)=>{
    if(event.sender!==studio.webContents)throw new Error('Untrusted automation sender');
    if(action==='config')return automation.snapshot();
    if(action==='configure')return automation.configure(data||{});
    if(action==='rotate')return automation.rotate();
    throw new Error('Unknown automation control');
  });
  const layout = () => { const [width, height] = window.getContentSize(); studio.setBounds({ x: 0, y: 54, width, height: Math.max(1, height - 54) }); for (const owned of hosts.values()) owned.layout(); };
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
  ipcMain.handle('studio:email-submit', async (event, link) => {
    if (!emailWindow || event.sender !== emailWindow.webContents) return { ok: false, message: 'Cửa sổ không được phép đăng nhập.' };
    if (emailNavigation) return { ok: false, message: 'Đang mở một liên kết đăng nhập. Vui lòng đợi.' };
    emailNavigation = true;
    try {
      await muse.openEmailLink(link);
      studio.webContents.send('studio:session-refresh');
      return { ok: true };
    } catch (error) {
      // Never print an email link, query parameters, or navigation error text.
      return { ok: false, message: /^MUSE_EMAIL_LINK_(INVALID|FAILED):/.test(error.message) ? error.message : 'Chưa mở được liên kết đăng nhập. Kiểm tra tab Muse rồi yêu cầu email mới nếu liên kết đã dùng hoặc hết hạn.' };
    } finally { emailNavigation = false; }
  });
  ipcMain.on('studio:email-close', event => { if (emailWindow && event.sender === emailWindow.webContents) emailWindow.close(); });
  ipcMain.handle('studio:view', async (event, name) => {
    if (event.sender !== window.webContents) throw new Error('Untrusted sender');
    if (name === 'studio') {
      for (const owned of hosts.values()) owned.hideLogin(); studio.webContents.focus();
      studio.webContents.send('studio:session-refresh');
    }
    else if (name === 'muse') await muse.connect(muse.selectedId);
    else if (name === 'reload-muse') { await muse.reopenLogin(); studio.webContents.send('studio:session-refresh'); }
    else if (name === 'login-diagnostics') {
      const report = loginLogs.get(muse.selectedId).snapshot({ version, loginVisible: host.loginVisible, account: muse.snapshot().find(account=>account.id===muse.selectedId) });
      const lines = report.events.slice(-8).map(event => `${event.time.slice(11,19)} ${event.method} ${event.route} → ${event.status || event.error}${event.setCookie ? ' · Có Set-Cookie' : ''}`);
      const result = await dialog.showMessageBox(window, { type: 'info', title: 'Chẩn đoán đăng nhập Muse',
        message: report.state === 'awaiting_code' ? 'Đang chờ mã xác nhận trên trang Muse' : report.verified ? 'Phiên đã được xác minh' : 'Chưa xác minh được phiên Muse',
        detail: `Bản ${version}. Báo cáo không chứa mã xác nhận, email, mật khẩu, cookie hoặc nội dung yêu cầu.\n${lines.length ? lines.join('\n') : 'Chưa ghi nhận phản hồi đăng nhập.'}`,
        buttons: ['Đóng','Sao chép chẩn đoán'],defaultId:0,cancelId:0 });
      if (result.response === 1) clipboard.writeText(JSON.stringify(report,null,2));
      if (host.loginVisible) host.login?.view.webContents.focus();
    }
    else if (name === 'email-link') {
      if (emailWindow && !emailWindow.isDestroyed()) { emailWindow.focus(); return; }
      emailWindow = new BrowserWindow({ parent: window, modal: true, width: 620, height: 430, resizable: false, autoHideMenuBar: true, title: 'Đăng nhập Muse từ email',
        webPreferences: { preload: path.join(directory, 'email-preload.cjs'), sandbox: true, contextIsolation: true, nodeIntegration: false, webSecurity: true } });
      emailWindow.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
      emailWindow.webContents.on('will-navigate', event => event.preventDefault());
      emailWindow.once('closed', () => { emailWindow = null; });
      await emailWindow.loadFile(path.join(directory, 'email-login.html'));
    }
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
  await automation?.close();
  await runtime?.close();
  for (const owned of hosts.values()) await owned.close();
  for (const id of hosts.keys()) await session.fromPartition(partitionFor(id)).cookies.flushStore();
  app.quit();
}
app.on('window-all-closed', () => app.quit());
app.on('before-quit', event => { if (!closing && runtime) { event.preventDefault(); void shutdown(); } });
