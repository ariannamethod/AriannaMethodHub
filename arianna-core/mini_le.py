import os
import random
from datetime import datetime

DATA_FILES = ["README.md", "Arianna-Method-v2.9.md"]
LOG_FILE = os.path.join("arianna-core", "log.txt")
HUMAN_LOG = os.path.join("arianna-core", "humanbridge.log")
MODEL_FILE = os.path.join("arianna-core", "model.txt")
EVOLUTION_FILE = os.path.join("arianna-core", "evolution_steps.py")


# simple character-level Markov model
def load_data():
    text = ""
    for f in DATA_FILES:
        with open(f, "r", encoding="utf-8") as fi:
            text += fi.read() + "\n"
    for path in [LOG_FILE, HUMAN_LOG]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fi:
                text += fi.read() + "\n"
    return text


def train(text):
    model = {}
    for a, b in zip(text, text[1:]):
        bucket = model.setdefault(a, {})
        bucket[b] = bucket.get(b, 0) + 1
    with open(MODEL_FILE, "w", encoding="utf-8") as f:
        for k, bucket in model.items():
            encoded = ",".join(f"{ch}:{count}" for ch, count in bucket.items())
            f.write(k + "\t" + encoded + "\n")
    return model


def load_model():
    model = {}
    if not os.path.exists(MODEL_FILE):
        return None
    with open(MODEL_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if "\t" not in line:
                # Skip malformed lines that lack a separator. These can appear
                # if the training data included newline characters or became
                # corrupted.
                continue
            k, encoded = line.rstrip("\n").split("\t", 1)
            freq = {}
            for pair in encoded.split(','):
                if ':' not in pair:
                    continue
                ch, count = pair.split(':', 1)
                if ch:
                    freq[ch] = int(count)
            if freq:
                model[k] = freq
    return model


def generate(model, length=80, seed=None):
    if not model:
        return ""
    ch = seed if seed in model else random.choice(list(model.keys()))
    out = [ch]
    for _ in range(length - 1):
        freq = model.get(ch)
        if not freq:
            ch = random.choice(list(model.keys()))
        else:
            chars = list(freq.keys())
            weights = list(freq.values())
            ch = random.choices(chars, weights=weights)[0]
        out.append(ch)
    return ''.join(out)


def update_index(comment):
    path = "index.html"
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    start = html.find('<div id="ai-comment">')
    if start != -1:
        end = html.find('</div>', start)
        comment_div = f'<div id="ai-comment">{comment}</div>'
        new_html = html[:start] + comment_div + html[end+6:]
    else:
        replacement = f'<div id="ai-comment">{comment}</div>\n</body>'
        new_html = html.replace('</body>', replacement)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_html)


def log_interaction(user_text: str, ai_text: str) -> None:
    with open(HUMAN_LOG, "a", encoding="utf-8") as f:
        timestamp = datetime.utcnow().isoformat()
        f.write(f"{timestamp} USER:{user_text} AI:{ai_text}\n")


def evolve(entry: str) -> None:
    """Append a small evolution step to a Python file."""
    if not os.path.exists(EVOLUTION_FILE):
        with open(EVOLUTION_FILE, "w", encoding="utf-8") as f:
            f.write("evolution_steps = []\n")
    with open(EVOLUTION_FILE, "a", encoding="utf-8") as f:
        f.write(f"evolution_steps.append({entry!r})\n")


def chat_response(user_text: str) -> str:
    text = load_data()
    model = train(text)
    seed = user_text[-1] if user_text else None
    reply = generate(model, seed=seed)
    log_interaction(user_text, reply)
    evolve(f"chat:{user_text[:10]}->{reply[:10]}")
    return reply


def run():
    text = load_data()
    model = train(text)
    comment = generate(model)
    previous = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            previous = [line.split(' ', 1)[1].strip() for line in lines]
    attempts = 0
    while comment in previous and attempts < 5:
        comment = generate(model)
        attempts += 1
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} {comment}\n")
    update_index(comment)
    evolve(f"ping:{comment[:10]}")


if __name__ == "__main__":
    run()
