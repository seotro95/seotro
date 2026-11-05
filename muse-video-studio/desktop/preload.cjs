const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('studioDesktop', Object.freeze({
  onAccount: callback => ipcRenderer.on('studio:account', (_event, id) => callback(id)),
  show: name => ipcRenderer.invoke('studio:view', name),
  onViewChanged: callback => ipcRenderer.on('studio:view-changed', (_event, name) => callback(name)),
  onVersion: callback => ipcRenderer.on('studio:version', (_event, version) => callback(version)),
}));
