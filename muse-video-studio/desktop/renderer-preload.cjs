const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('museTransport', Object.freeze({
  request: (id, endpoint, data) => ipcRenderer.invoke('studio:api', { id, endpoint, data }),
  cancel: id => ipcRenderer.send('studio:cancel', id),
  onSessionRefresh: callback => {
    const listener = () => callback();
    ipcRenderer.on('studio:session-refresh', listener);
    return () => ipcRenderer.removeListener('studio:session-refresh', listener);
  },
}));
