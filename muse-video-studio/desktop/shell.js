const message = document.querySelector('#message');
window.studioDesktop.onVersion(version => { document.querySelector('nav strong').textContent = `MUSE AI STUDIO ${version}`; });
for (const name of ['studio', 'muse', 'email-link', 'reload-muse', 'login-diagnostics']) document.getElementById(name).onclick = async () => {
  message.textContent = '';
  try { await window.studioDesktop.show(name); }
  catch (error) { message.textContent = error.message; message.title = error.message; }
};
window.studioDesktop.onViewChanged(name => {
  for (const key of ['studio', 'muse']) document.getElementById(key).setAttribute('aria-pressed', String(key === name));
});
