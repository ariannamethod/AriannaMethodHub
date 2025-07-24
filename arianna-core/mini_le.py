import os
import random
from datetime import datetime

DATA_FILES = ["README.md", "Arianna-Method-v2.9.md"]
LOG_FILE = os.path.join("arianna-core", "log.txt")
MODEL_FILE = os.path.join("arianna-core", "model.txt")

# simple character-level Markov model
def load_data():
    text = ""
    for f in DATA_FILES:
        with open(f, "r", encoding="utf-8") as fi:
            text += fi.read() + "\n"
    return text

def train(text):
    model = {}
    for a, b in zip(text, text[1:]):
        model.setdefault(a, []).append(b)
    with open(MODEL_FILE, "w", encoding="utf-8") as f:
        for k, vals in model.items():
            f.write(k + "\t" + ''.join(vals) + "\n")
    return model

def load_model():
    model = {}
    if not os.path.exists(MODEL_FILE):
        return None
    with open(MODEL_FILE, "r", encoding="utf-8") as f:
        for line in f:
            k, vals = line.rstrip().split("\t")
            model[k] = list(vals)
    return model

def generate(model, length=80):
    if not model:
        return ""
    ch = random.choice(list(model.keys()))
    out = [ch]
    for _ in range(length - 1):
        next_chars = model.get(ch, model[random.choice(list(model.keys()))])
        ch = random.choice(next_chars)
        out.append(ch)
    return ''.join(out)

def update_index(comment):
    path = "index.html"
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    start = html.find('<div id="ai-comment">')
    if start != -1:
        end = html.find('</div>', start)
        new_html = html[:start] + f'<div id="ai-comment">{comment}</div>' + html[end+6:]
    else:
        new_html = html.replace('</body>', f'<div id="ai-comment">{comment}</div>\n</body>')
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_html)

def run():
    text = load_data()
    model = load_model()
    if model is None:
        model = train(text)
    comment = generate(model)
    previous = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            previous = [line.split(' ', 1)[1].strip() for line in f.readlines()]
    attempts = 0
    while comment in previous and attempts < 5:
        comment = generate(model)
        attempts += 1
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} {comment}\n")
    update_index(comment)

if __name__ == "__main__":
    run()
