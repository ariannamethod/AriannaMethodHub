import os
import random
import json
from datetime import datetime

CORE_FILES = ["README.md", "Arianna-Method-v2.9.md"]
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "datasets")
STATE_FILE = os.path.join("arianna_core", "dataset_state.json")
LOG_FILE = os.path.join("arianna_core", "log.txt")
HUMAN_LOG = os.path.join("arianna_core", "humanbridge.log")
MODEL_FILE = os.path.join("arianna_core", "model.txt")
EVOLUTION_FILE = os.path.join("arianna_core", "evolution_steps.py")
LOG_MAX_BYTES = 1_000_000  # 1 MB default size limit for rotation


def rotate_log(path: str, max_bytes: int = LOG_MAX_BYTES) -> None:
    """Rotate the given log file if it exceeds ``max_bytes``."""
    if os.path.exists(path) and os.path.getsize(path) > max_bytes:
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        os.rename(path, f"{path}.{timestamp}")

# dataset helpers
def _dataset_snapshot() -> dict:
    """Return a mapping of dataset file name to size."""
    snapshot = {}
    if os.path.isdir(DATA_DIR):
        for name in os.listdir(DATA_DIR):
            path = os.path.join(DATA_DIR, name)
            if os.path.isfile(path):
                snapshot[name] = os.path.getsize(path)
    return snapshot


def check_dataset_updates() -> None:
    """Update ``STATE_FILE`` if the dataset contents changed."""
    current = _dataset_snapshot()
    previous = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            try:
                previous = json.load(f)
            except json.JSONDecodeError:
                previous = {}
    if current != previous:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f)


def get_data_files() -> list:
    """Return the list of corpus files."""
    files = [f for f in CORE_FILES if os.path.exists(f)]
    if os.path.isdir(DATA_DIR):
        for name in sorted(os.listdir(DATA_DIR)):
            path = os.path.join(DATA_DIR, name)
            if os.path.isfile(path):
                files.append(path)
    return files

# simple character-level Markov model
def load_data():
    check_dataset_updates()
    text = ""
    for f in get_data_files():
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
        json.dump(model, f)
    return model


def _load_legacy_model(path: str) -> dict:
    """Parse the old colon-separated format."""
    model = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if "\t" not in line:
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


def load_model():
    if not os.path.exists(MODEL_FILE):
        return None
    try:
        with open(MODEL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        model = _load_legacy_model(MODEL_FILE)
        with open(MODEL_FILE, "w", encoding="utf-8") as f:
            json.dump(model, f)
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
    rotate_log(HUMAN_LOG, LOG_MAX_BYTES)
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
    rotate_log(LOG_FILE, LOG_MAX_BYTES)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} {comment}\n")
    update_index(comment)
    evolve(f"ping:{comment[:10]}")


if __name__ == "__main__":
    run()
