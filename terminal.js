const output = document.getElementById('terminal');
const input = document.getElementById('user-input');
const form = document.getElementById('input-form');

fetch('index_full.html')
  .then(r => r.text())
  .then(text => typeText(text));

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
    .then(r => r.text())
    .then(t => {
      output.textContent += '\n' + t + '\n';
    });
  input.value = '';
});

input.disabled = true;
