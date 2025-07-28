const output = document.getElementById('terminal');
const input = document.getElementById('user-input');
const form = document.getElementById('input-form');

function print(text) {
  output.textContent += text + '\n';
  output.scrollTop = output.scrollHeight;
}

fetch('index_full.html')
  .then(r => r.text())
  .then((html) => {
    const div = document.createElement('div');
    div.innerHTML = html;
    print(div.innerText.trim());
  });

form.addEventListener('submit', e => {
  e.preventDefault();
  const msg = input.value.trim();
  if (!msg) return;
  print('$ ' + msg);
  fetch('/chat?msg=' + encodeURIComponent(msg))
    .then((r) => {
      if (!r.ok) {
        throw new Error(r.status + ' ' + r.statusText);
      }
      return r.text();
    })
    .then((t) => print('Le: ' + t))
    .catch((err) => print('[server error: ' + err.message + ']'));
  input.value = '';
});
