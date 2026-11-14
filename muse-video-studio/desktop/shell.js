const message = document.querySelector('#message');
let selectedView = 'studio';
let startupState = {phase:'loading',message:'Đang tải giao diện trên máy này.',code:'loading'};
function renderStartup(){
  document.querySelector('#startup').hidden=selectedView!=='studio'||startupState.phase==='ready';
  document.querySelector('#startup-title').textContent=startupState.phase==='error'?'Chưa mở được Studio':'Đang mở Studio…';
  document.querySelector('#startup-message').textContent=startupState.message;
  document.querySelector('#startup-code').textContent=startupState.phase==='error'?startupState.code:'';
  document.querySelector('#startup-exit').textContent=startupState.phase==='error'&&startupState.lastExit?`Lý do: ${startupState.lastExit.reason} · Mã thoát: ${startupState.lastExit.exitCodeHex??'chưa có'} · Bước: ${startupState.lastExit.stage}`:'';
}
window.studioDesktop.onStartup(state=>{startupState=state;renderStartup()});
window.studioDesktop.startup('status').then(state=>{startupState=state;renderStartup()}).catch(()=>{message.textContent='Chưa đọc được trạng thái Studio.'});
for(const [id,action] of [['reload-studio','retry'],['retry-studio','retry'],['recover-studio','recover'],['copy-startup','copy']])document.getElementById(id).onclick=async()=>{
  const button=document.getElementById(id);button.disabled=true;
  try{await window.studioDesktop.startup(action);message.textContent=action==='copy'?'Đã sao chép chẩn đoán Studio.':''}
  catch(error){message.textContent=error.message}
  finally{button.disabled=false}
};
window.studioDesktop.onVersion(version => { document.querySelector('nav strong').textContent = `MUSE AI STUDIO ${version}`; });
for (const name of ['studio', 'muse', 'email-link', 'reload-muse', 'login-diagnostics']) document.getElementById(name).onclick = async () => {
  message.textContent = '';
  try { await window.studioDesktop.show(name); }
  catch (error) { message.textContent = error.message; message.title = error.message; }
};
window.studioDesktop.onViewChanged(name => {
  selectedView=name;renderStartup();
  for (const key of ['studio', 'muse']) document.getElementById(key).setAttribute('aria-pressed', String(key === name));
});

window.studioDesktop.onAccount(id=>{document.querySelector('nav span').textContent=`Đăng nhập đang chọn: Muse ${String(id).padStart(2,'0')}`});
