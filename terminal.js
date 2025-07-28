const output = document.getElementById('terminal');
const input = document.getElementById('user-input');
const form = document.getElementById('input-form');

function print(text) {
  output.textContent += text + '\n';
  output.scrollTop = output.scrollHeight;
}

fetch('index_full.html')
  .then(r => r.text())
  .then(t => print(t));

form.addEventListener('submit', e => {
  e.preventDefault();
  const msg = input.value.trim();
  if (!msg) return;
  print('$ ' + msg);
  fetch('/chat?msg=' + encodeURIComponent(msg))
    .then(r => r.text())
    .then(t => print('Le: ' + t))
    .catch(() => print('[server unavailable]'));
  input.value = '';
});
