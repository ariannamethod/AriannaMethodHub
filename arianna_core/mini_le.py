import os
import random
import json
import sqlite3
import gzip
import shutil
from datetime import datetime

from .evolution_safe import evolve_cycle
CORE_FILES = ["README.md", "Arianna-Method-v2.9.md"]
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "datasets")
STATE_FILE = os.path.join("arianna_core", "dataset_state.json")
LOG_FILE = os.path.join("arianna_core", "log.txt")
HUMAN_LOG = os.path.join("arianna_core", "humanbridge.log")
MODEL_FILE = os.path.join("arianna_core", "model.txt")
EVOLUTION_FILE = os.path.join("arianna_core", "evolution_steps.py")
MEMORY_DB = os.path.join("arianna_core", "memory.db")
LOG_MAX_BYTES = 1_000_000  # 1 MB default size limit for rotation
NGRAM_SIZE = 2


def rotate_log(path: str, max_bytes: int = LOG_MAX_BYTES) -> None:
    """Rotate the given log file if it exceeds ``max_bytes``."""
    if os.path.exists(path) and os.path.getsize(path) > max_bytes:
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        archive = f"{path}.{timestamp}.gz"
        with open(path, "rb") as src, gzip.open(archive, "wb") as dst:
            shutil.copyfileobj(src, dst)
        os.remove(path)
        with open(path + ".index", "a", encoding="utf-8") as f:
            f.write(f"{archive}\n")


def search_logs(query: str, path: str = HUMAN_LOG) -> list:
    """Return lines containing ``query`` from current and archived logs."""
    results = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if query in line:
                    results.append(line.strip())
    index = path + ".index"
    if os.path.exists(index):
        with open(index, "r", encoding="utf-8") as f:
            archives = [line.strip() for line in f if line.strip()]
        for gz in archives:
            if os.path.exists(gz):
                with gzip.open(gz, "rt", encoding="utf-8") as gzf:
                    for line in gzf:
                        if query in line:
                            results.append(line.strip())
    return results


def record_pattern(pattern: str) -> None:
    """Persist ``pattern`` occurrence in the SQLite memory."""
    conn = sqlite3.connect(MEMORY_DB)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS patterns (pattern TEXT PRIMARY KEY, count INTEGER)"
    )
    conn.execute(
        "INSERT INTO patterns(pattern, count) VALUES(?, 1) "
        "ON CONFLICT(pattern) DO UPDATE SET count=count+1",
        (pattern,),
    )
    conn.commit()
    conn.close()


def health_report() -> dict:
    """Return basic health metrics for the system."""
    report = {
        "model_exists": os.path.exists(MODEL_FILE),
        "model_size": os.path.getsize(MODEL_FILE) if os.path.exists(MODEL_FILE) else 0,
        "log_size": os.path.getsize(LOG_FILE) if os.path.exists(LOG_FILE) else 0,
        "human_log_size": os.path.getsize(HUMAN_LOG) if os.path.exists(HUMAN_LOG) else 0,
    }
    try:
        model = load_model()
        sample = generate(model, 20) if model else ""
        report["generation_ok"] = bool(sample)
    except Exception:
        report["generation_ok"] = False
    return report

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


def train(text: str, n: int = NGRAM_SIZE):
    """Train an ``n``-gram model from ``text``."""
    if n < 2:
        n = 2
    model = {}
    for i in range(len(text) - n + 1):
        ctx = text[i : i + n - 1]
        nxt = text[i + n - 1]
        bucket = model.setdefault(ctx, {})
        bucket[nxt] = bucket.get(nxt, 0) + 1
    with open(MODEL_FILE, "w", encoding="utf-8") as f:
        json.dump({"n": n, "model": model}, f)
    return {"n": n, "model": model}


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
            data = json.load(f)
        return data
    except json.JSONDecodeError:
        model = _load_legacy_model(MODEL_FILE)
        with open(MODEL_FILE, "w", encoding="utf-8") as f:
            json.dump({"n": 2, "model": model}, f)
        return {"n": 2, "model": model}


def generate(model, length: int = 80, seed: str | None = None) -> str:
    """Generate text from a trained model."""
    if not model:
        return ""
    if "model" in model:
        n = model.get("n", 2)
        m = model["model"]
    else:
        n = 2
        m = model
    context = None
    if seed:
        context = seed[-(n - 1) :]
    if not context or context not in m:
        context = random.choice(list(m.keys()))
    out = context
    for _ in range(length - len(context)):
        freq = m.get(context)
        if not freq:
            context = random.choice(list(m.keys()))
            if len(out) + len(context) > length:
                break
            out += context
            continue
        chars = list(freq.keys())
        weights = list(freq.values())
        ch = random.choices(chars, weights=weights)[0]
        out += ch
        context = out[-(n - 1) :]
    return out[:length]


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
    record_pattern(user_text)


def evolve(entry: str) -> None:
    """Append a small evolution step to a Python file."""
    if not os.path.exists(EVOLUTION_FILE):
        with open(EVOLUTION_FILE, "w", encoding="utf-8") as f:
            f.write(
                "evolution_steps = {'chat': [], 'ping': [], 'resonance': [], 'error': []}\n"
            )
    category, payload = (entry.split(":", 1) + [""])[0:2]
    if category not in {"chat", "ping", "resonance", "error"}:
        category = "error"
        payload = entry
    with open(EVOLUTION_FILE, "a", encoding="utf-8") as f:
        f.write(f"evolution_steps['{category}'].append({payload!r})\n")


def chat_response(user_text: str) -> str:
    text = load_data()
    model = train(text)
    seed = user_text[-1] if user_text else None
    reply = generate(model, seed=seed)
    log_interaction(user_text, reply)
    record_pattern(reply)
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
    record_pattern(comment)
    update_index(comment)
    evolve(f"ping:{comment[:10]}")
    try:
        evolve_cycle()
    except Exception as e:
        print("evolve_cycle failed:", e)


if __name__ == "__main__":
    run()
