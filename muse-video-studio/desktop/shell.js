const message = document.querySelector('#message');
for (const name of ['studio', 'muse']) document.getElementById(name).onclick = async () => {
  message.textContent = '';
  try { await window.studioDesktop.show(name); }
  catch (error) { message.textContent = error.message; }
};
window.studioDesktop.onViewChanged(name => {
  for (const key of ['studio', 'muse']) document.getElementById(key).setAttribute('aria-pressed', String(key === name));
});
