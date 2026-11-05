const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('museEmailLogin', Object.freeze({
  submit: link => ipcRenderer.invoke('studio:email-submit', link),
  close: () => ipcRenderer.send('studio:email-close'),
}));
