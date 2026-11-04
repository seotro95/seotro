const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('studioDesktop', Object.freeze({
  show: name => ipcRenderer.invoke('studio:view', name),
  onViewChanged: callback => ipcRenderer.on('studio:view-changed', (_event, name) => callback(name)),
}));
