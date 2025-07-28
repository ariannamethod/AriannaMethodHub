const output = document.getElementById('terminal');
const input = document.getElementById('user-input');
const form = document.getElementById('input-form');

fetch('index_full.html')
  .then(r => {
    if (!r.ok) throw new Error('failed to load index_full.html');
    return r.text();
  })
  .then(text => typeText(text))
  .catch(() => {
    output.textContent =
      'Error loading content. Run `python3 -m http.server` or `./serve.sh` and open http://localhost:8000/index.html';
    input.disabled = false;
  });

function typeText(text) {
  let i = 0;
  const speed = 20;
  function step() {
    if (i < text.length) {
      output.textContent += text[i++];
      setTimeout(step, speed);
    } else {
      blinkCursor();
      input.disabled = false;
      input.focus();
    }
  }
  step();
}

function blinkCursor() {
  const cursor = document.createElement('span');
  cursor.className = 'cursor';
  cursor.textContent = '_';
  output.appendChild(cursor);
  setInterval(() => {
    cursor.style.visibility = cursor.style.visibility === 'hidden' ? 'visible' : 'hidden';
  }, 500);
}

form.addEventListener('submit', e => {
  e.preventDefault();
  const msg = input.value;
  fetch('/chat?msg=' + encodeURIComponent(msg))
    .then(r => {
      if (!r.ok) throw new Error('server error');
      return r.text();
    })
    .then(t => {
      output.textContent += '\n' + t + '\n';
    })
    .catch(() => {
      output.textContent += '\n[server not running]\n';
    });
  input.value = '';
});

input.disabled = true;
