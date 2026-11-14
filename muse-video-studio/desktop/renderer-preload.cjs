const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('museTransport', Object.freeze({
  rendererStage: stage => { if(['bootstrap','workspace','interface','media-library','ready'].includes(stage))ipcRenderer.send('studio:renderer-stage',stage); },
  rendererState: state => { if(state==='ready'||state==='error')ipcRenderer.send('studio:renderer-state',state); },
  dataControl: action => ipcRenderer.invoke('studio:data-control',action),
  automationControl: (action,data) => ipcRenderer.invoke('studio:automation-control',action,data),
  onAutomation: callback => {
    const listener=async(_event,{id,action,data})=>{try{const reply=await callback(action,data);ipcRenderer.send('studio:automation-reply',{id,ok:reply.ok===true,result:reply.result,error:reply.error,status:reply.status})}catch(error){ipcRenderer.send('studio:automation-reply',{id,ok:false,error:error.message,status:error.status})}};
    ipcRenderer.on('studio:automation-command',listener);ipcRenderer.send('studio:automation-ready',true);
    return ()=>{ipcRenderer.removeListener('studio:automation-command',listener);ipcRenderer.send('studio:automation-ready',false)};
  },
  request: (id, endpoint, data) => ipcRenderer.invoke('studio:api', { id, endpoint, data }),
  cancel: id => ipcRenderer.send('studio:cancel', id),
  export: (action, data) => ipcRenderer.invoke('studio:export', action, data),
  onSessionRefresh: callback => {
    const listener = () => callback();
    ipcRenderer.on('studio:session-refresh', listener);
    return () => ipcRenderer.removeListener('studio:session-refresh', listener);
  },
}));
ipcRenderer.send('studio:renderer-stage','bootstrap');
