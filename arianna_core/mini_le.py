import os
import random
import json
import gzip
import shutil
from datetime import datetime

from .evolution_safe import evolve_cycle
from . import memory
CORE_FILES = ["README.md", "Arianna-Method-v2.9.md"]
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "datasets")
STATE_FILE = os.path.join("arianna_core", "dataset_state.json")
LOG_FILE = os.path.join("arianna_core", "log.txt")
HUMAN_LOG = os.path.join("arianna_core", "humanbridge.log")
MODEL_FILE = os.path.join("arianna_core", "model.txt")
EVOLUTION_FILE = os.path.join("arianna_core", "evolution_steps.py")
EVOLUTION_METRICS = os.path.join("arianna_core", "evolution_metrics.json")
LOG_MAX_BYTES = 1_000_000  # 1 MB default size limit for rotation


def rotate_log(path: str, max_bytes: int = LOG_MAX_BYTES) -> None:
    """Rotate and compress ``path`` if it exceeds ``max_bytes``."""
    if os.path.exists(path) and os.path.getsize(path) > max_bytes:
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        archive = f"{path}.{timestamp}.gz"
        with open(path, "rb") as src, gzip.open(archive, "wb") as dst:
            shutil.copyfileobj(src, dst)
        os.remove(path)
        idx = path + ".index"
        with open(idx, "a", encoding="utf-8") as f:
            f.write(f"{timestamp} {archive}\n")

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


def train(text: str, n: int = 1):
    """Train an n-gram model from ``text``."""
    model = {}
    if n < 1:
        n = 1
    for i in range(len(text) - n):
        key = text[i : i + n]
        nxt = text[i + n]
        bucket = model.setdefault(key, {})
        bucket[nxt] = bucket.get(nxt, 0) + 1
    with open(MODEL_FILE, "w", encoding="utf-8") as f:
        json.dump(model, f)
    memory.update_patterns(model)
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


def generate(model, length: int = 80, seed: str | None = None, n: int = 1) -> str:
    if not model:
        return ""
    key = seed if seed in model else random.choice(list(model.keys()))
    out = [key]
    for _ in range(length - n):
        freq = model.get(key)
        if not freq:
            key = random.choice(list(model.keys()))
        else:
            chars = list(freq.keys())
            weights = list(freq.values())
            nxt = random.choices(chars, weights=weights)[0]
            key = key[1:] + nxt if n > 1 else nxt
        out.append(key[-1])
    return "".join(out)


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
    category = entry.split(":", 1)[0] if ":" in entry else "misc"
    metrics = {}
    if os.path.exists(EVOLUTION_METRICS):
        with open(EVOLUTION_METRICS, "r", encoding="utf-8") as m:
            try:
                metrics = json.load(m)
            except json.JSONDecodeError:
                metrics = {}
    metrics[category] = metrics.get(category, 0) + 1
    with open(EVOLUTION_METRICS, "w", encoding="utf-8") as m:
        json.dump(metrics, m)


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
    try:
        evolve_cycle()
    except Exception as e:
        print("evolve_cycle failed:", e)


if __name__ == "__main__":
    run()
