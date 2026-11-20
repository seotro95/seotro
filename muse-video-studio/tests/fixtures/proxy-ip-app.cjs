const {app,BrowserWindow}=require('electron');
let window;globalThis.proxyIP=import('../../desktop/proxy-ip.mjs');
app.whenReady().then(()=>{window=new BrowserWindow({show:false,webPreferences:{sandbox:true}});return window.loadURL('about:blank')});
