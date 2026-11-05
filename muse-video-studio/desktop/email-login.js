const input = document.querySelector('#email-link');
const button = document.querySelector('#submit');
const feedback = document.querySelector('#feedback');
document.querySelector('#cancel').onclick = () => window.museEmailLogin.close();
document.querySelector('#email-form').onsubmit = async event => {
  event.preventDefault();
  const link = input.value; input.value = '';
  button.disabled = true; feedback.textContent = 'Đang mở liên kết trong phiên Muse của tool…';
  try {
    const result = await window.museEmailLogin.submit(link);
    if (result.ok) window.museEmailLogin.close();
    else feedback.textContent = result.message;
  } catch { feedback.textContent = 'Chưa mở được liên kết. Vui lòng đóng cửa sổ này và thử lại.'; }
  finally { button.disabled = false; }
};
