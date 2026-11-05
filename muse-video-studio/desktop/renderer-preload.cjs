const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('museTransport', Object.freeze({
  request: (id, endpoint, data) => ipcRenderer.invoke('studio:api', { id, endpoint, data }),
  cancel: id => ipcRenderer.send('studio:cancel', id),
  export: (action, data) => ipcRenderer.invoke('studio:export', action, data),
  onSessionRefresh: callback => {
    const listener = () => callback();
    ipcRenderer.on('studio:session-refresh', listener);
    return () => ipcRenderer.removeListener('studio:session-refresh', listener);
  },
}));
