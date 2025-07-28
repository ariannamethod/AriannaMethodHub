import os
import random
import json
import sqlite3
import gzip
import shutil
from datetime import datetime
from typing import Dict

from . import nanogpt_bridge

from .evolution_safe import evolve_cycle
from .config import settings
CORE_FILES = ["README.md", "Arianna-Method-v2.9.md", "index.html", "le_persona_prompt.md"]
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "datasets")
STATE_FILE = os.path.join("arianna_core", "dataset_state.json")
LOG_FILE = os.path.join("arianna_core", "log.txt")
HUMAN_LOG = os.path.join("arianna_core", "humanbridge.log")
MODEL_FILE = os.path.join("arianna_core", "model.txt")
EVOLUTION_FILE = os.path.join("arianna_core", "evolution_steps.py")
MEMORY_DB = os.path.join("arianna_core", "memory.db")
LOG_MAX_BYTES = 1_000_000  # 1 MB default size limit for rotation
NGRAM_LEVEL = settings.n_gram_level
CHAT_SESSION_COUNT = 0
REPRO_FILE = os.path.join("arianna_core", "last_reproduction.txt")
LAST_ACTIVITY_FILE = os.path.join("arianna_core", "last_activity.txt")
DREAM_LOG = os.path.join("arianna_core", "dream.log")
IMMUNE_BLOCKED = 0
RECENT_NOVELTY = 0.0
TOXIC_WORDS = {"kill", "hate", "badword"}
UTIL_STATE_FILE = os.path.join("arianna_core", "util_state.json")
UTIL_CHANGE_LOG = os.path.join("arianna_core", "util_changes.log")
LOG_STATE_FILE = os.path.join("arianna_core", "log_state.json")
LOG_CHANGE_LOG = os.path.join("arianna_core", "log_changes.log")


def _allowed_messages() -> int:
    """Return the number of allowed chat messages based on log size."""
    size = os.path.getsize(HUMAN_LOG) if os.path.exists(HUMAN_LOG) else 0
    return max(1, size // 1000 + 3)


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
        prune_archives(path)


def prune_archives(path: str, keep: int = 5) -> None:
    """Remove old log archives keeping only the most recent ``keep``."""
    index = path + ".index"
    if not os.path.exists(index):
        return
    with open(index, "r", encoding="utf-8") as f:
        archives = [line.strip() for line in f if line.strip()]
    if len(archives) <= keep:
        return
    to_remove = archives[:-keep]
    for gz in to_remove:
        if os.path.exists(gz):
            os.remove(gz)
    with open(index, "w", encoding="utf-8") as f:
        f.write("\n".join(archives[-keep:]) + "\n")


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


def metabolize_input(text: str, n: int | None = None) -> float:
    """Return novelty ratio of ``text`` based on the current model."""
    model = load_model()
    if not model:
        return 1.0
    if n is None:
        n = model.get("n", 2) if isinstance(model, dict) else NGRAM_LEVEL
    m = model["model"] if "model" in model else model
    total = max(1, len(text) - n + 1)
    unseen = 0
    for i in range(total):
        ctx = text[i : i + n - 1]
        if ctx not in m:
            unseen += 1
    return unseen / total


def immune_filter(text: str) -> bool:
    """Return ``True`` if ``text`` is acceptable; increment counter if not."""
    global IMMUNE_BLOCKED
    lowered = text.lower()
    if any(bad in lowered for bad in TOXIC_WORDS):
        IMMUNE_BLOCKED += 1
        return False
    return True


def adaptive_mutation(model: Dict) -> Dict:
    """Apply a random mutation and keep it if novelty improves."""
    if not model:
        return model
    orig_sample = generate(model, 20)
    baseline = metabolize_input(orig_sample, n=model.get("n", 2))
    mutated = json.loads(json.dumps(model))
    m = mutated["model"] if "model" in mutated else mutated
    ctx = random.choice(list(m.keys()))
    freq = m[ctx]
    ch = random.choice(list(freq.keys()))
    delta = random.choice([-1, 1])
    freq[ch] = max(1, freq.get(ch, 1) + delta)
    new_sample = generate(mutated, 20)
    if metabolize_input(new_sample, n=mutated.get("n", 2)) >= baseline:
        return mutated
    return model


def reproduction_cycle() -> Dict:
    """Retrain the model and apply an adaptive mutation."""
    text = load_data()
    model = train(text)
    improved = adaptive_mutation(model)
    with open(REPRO_FILE, "w", encoding="utf-8") as f:
        f.write(datetime.utcnow().isoformat())
    with open(MODEL_FILE, "w", encoding="utf-8") as f:
        json.dump(improved, f)
    return improved


def dream_cycle(threshold: int = 300) -> str | None:
    """Generate autonomous output when user activity is low."""
    if os.path.exists(LAST_ACTIVITY_FILE):
        with open(LAST_ACTIVITY_FILE, "r", encoding="utf-8") as f:
            ts = f.read().strip()
        try:
            last = datetime.fromisoformat(ts)
        except ValueError:
            last = datetime.utcnow()
        if (datetime.utcnow() - last).total_seconds() < threshold:
            return None
    model = load_model()
    if not model:
        return None
    dream = generate(model, length=60)
    with open(DREAM_LOG, "a", encoding="utf-8") as f:
        f.write(dream + "\n")
    record_pattern(dream)
    log_interaction("[DREAM]", dream)
    return dream


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
        report["recent_novelty"] = metabolize_input(sample) if sample else 0.0
    except Exception:
        report["generation_ok"] = False
        report["recent_novelty"] = 0.0
    report["immune_blocked"] = IMMUNE_BLOCKED
    if os.path.exists(REPRO_FILE):
        with open(REPRO_FILE, "r", encoding="utf-8") as f:
            report["last_reproduction"] = f.read().strip()
    else:
        report["last_reproduction"] = None
    return report


def resonance_report() -> dict:
    """Return resonance metrics based on pattern memory."""
    conn = sqlite3.connect(MEMORY_DB)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS patterns (pattern TEXT PRIMARY KEY, count INTEGER)"
    )
    rows = conn.execute("SELECT count FROM patterns").fetchall()
    conn.close()
    total = len(rows)
    repeated = sum(1 for (c,) in rows if c > 1)
    freq = repeated / total if total else 0.0
    return {
        "total_patterns": total,
        "repeated_patterns": repeated,
        "resonance_frequency": freq,
    }


def adjust_response_style(reply: str) -> str:
    """Return reply adjusted based on resonance frequency."""
    metrics = resonance_report()
    if metrics["resonance_frequency"] > 0.3:
        return reply + "!"
    return reply

# dataset helpers
def _dataset_snapshot() -> dict:
    """Return a mapping of dataset file name to size."""
    snapshot = {}
    if os.path.isdir(DATA_DIR):
        for name in os.listdir(DATA_DIR):
            path = os.path.join(DATA_DIR, name)
            if os.path.isfile(path):
                snapshot[name] = os.path.getsize(path)
    for name in CORE_FILES:
        if os.path.exists(name):
            snapshot[name] = os.path.getsize(name)
    return snapshot


def _utility_snapshot() -> dict:
    """Return a mapping of utility file paths to modification times."""
    snapshot = {}
    for root, _, files in os.walk("arianna_core"):
        for name in files:
            if name.endswith(".py"):
                path = os.path.join(root, name)
                snapshot[path] = os.path.getmtime(path)
    return snapshot


def check_utility_updates() -> None:
    """Log utility changes and trigger retraining if needed."""
    current = _utility_snapshot()
    previous = {}
    if os.path.exists(UTIL_STATE_FILE):
        with open(UTIL_STATE_FILE, "r", encoding="utf-8") as f:
            try:
                previous = json.load(f)
            except json.JSONDecodeError:
                previous = {}
    changed = [p for p, m in current.items() if previous.get(p) != m]
    removed = [p for p in previous if p not in current]
    if changed or removed:
        with open(UTIL_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f)
        with open(UTIL_CHANGE_LOG, "a", encoding="utf-8") as log:
            timestamp = datetime.utcnow().isoformat()
            entries = ",".join(changed + removed)
            log.write(f"{timestamp} {entries}\n")
        reproduction_cycle()


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
        reproduction_cycle()


def _logs_snapshot() -> dict:
    """Return a mapping of log file paths to modification times."""
    snapshot = {}
    for path in [LOG_FILE, HUMAN_LOG, DREAM_LOG]:
        if os.path.exists(path):
            snapshot[path] = os.path.getmtime(path)
    return snapshot


def check_log_updates() -> None:
    """Trigger retraining when log files change."""
    current = _logs_snapshot()
    previous = {}
    if os.path.exists(LOG_STATE_FILE):
        with open(LOG_STATE_FILE, "r", encoding="utf-8") as f:
            try:
                previous = json.load(f)
            except json.JSONDecodeError:
                previous = {}
    changed = [p for p, m in current.items() if previous.get(p) != m]
    if changed:
        with open(LOG_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f)
        with open(LOG_CHANGE_LOG, "a", encoding="utf-8") as log:
            timestamp = datetime.utcnow().isoformat()
            log.write(f"{timestamp} {','.join(changed)}\n")
        reproduction_cycle()


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
    for path in [LOG_FILE, HUMAN_LOG, DREAM_LOG]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fi:
                text += fi.read() + "\n"
    return text


def train(text: str, n: int | None = None):
    """Train an ``n``-gram model from ``text``."""
    if n is None:
        n = NGRAM_LEVEL
        length = len(text)
        if length > 10000:
            n = max(n, 3)
        if length > 50000:
            n = max(n, 4)
    if n < 2:
        n = 2
    model = {}
    for i in range(len(text) - n + 1):
        ctx = text[i : i + n - 1]
        nxt = text[i + n - 1]
        bucket = model.setdefault(ctx, {})
        bucket[nxt] = bucket.get(nxt, 0) + 1
    # simple size optimization for large n-grams
    if n > 3 and len(model) > 50000:
        model = {c: f for c, f in model.items() if max(f.values()) > 1}
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


def generate(
    model, length: int = 80, seed: str | None = None,
    *, rng: random.Random | None = None, backoff_threshold: int = 1
) -> str:
    """Generate text from a trained model with optional backoff.

    Parameters
    ----------
    model : dict
        Trained n-gram model.
    length : int, optional
        Number of characters to generate. Default is ``80``.
    seed : str | None, optional
        Optional seed string used to initialize the context.
    rng : random.Random | None, optional
        Random number generator instance. When provided the sequence is
        deterministic and isolated from the global RNG state.
    backoff_threshold : int, optional
        Number of consecutive missing contexts before falling back to a random
        context. Default is ``1``.
    """
    rng = rng or random
    if not model:
        return ""
    if "model" in model:
        n = model.get("n", 2)
        m = model["model"]
    else:
        n = 2
        m = model
    context = seed[-(n - 1) :] if seed else None
    if not context or context not in m:
        if seed and n > 2:
            fallback = seed[-1:]
            if fallback in m:
                context = fallback
                n = 2
        if not context or context not in m:
            context = rng.choice(list(m.keys()))
            n = len(context) + 1
    out = context
    missing = 0
    for _ in range(length - len(context)):
        freq = m.get(context)
        if not freq:
            missing += 1
            if n > 2:
                context = context[-1:]
                n = 2
                freq = m.get(context)
        if not freq:
            if missing >= backoff_threshold:
                context = rng.choice(list(m.keys()))
                n = len(context) + 1
                missing = 0
                if len(out) + len(context) > length:
                    break
                out += context
            continue
        else:
            missing = 0
        chars = list(freq.keys())
        weights = list(freq.values())
        ch = rng.choices(chars, weights=weights)[0]
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
    with open(LAST_ACTIVITY_FILE, "w", encoding="utf-8") as la:
        la.write(timestamp)


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


def chat_response(user_text: str, *, use_nanogpt: bool | None = None) -> str:
    global CHAT_SESSION_COUNT, RECENT_NOVELTY
    if use_nanogpt is None:
        use_nanogpt = settings.use_nanogpt

    check_utility_updates()
    check_log_updates()
    allowed = _allowed_messages()
    if CHAT_SESSION_COUNT >= allowed:
        return "MESSAGE LIMIT REACHED"
    if not immune_filter(user_text):
        return "CONTENT BLOCKED"
    CHAT_SESSION_COUNT += 1
    RECENT_NOVELTY = metabolize_input(user_text)
    reply = None
    if use_nanogpt:
        try:
            reply = nanogpt_bridge.generate(user_text)
        except Exception:
            reply = None
    if not reply:
        text = load_data()
        model = train(text)
        seed = user_text[-1] if user_text else None
        reply = generate(model, seed=seed)
    reply = adjust_response_style(reply)
    log_interaction(user_text, reply)
    record_pattern(reply)
    evolve(f"chat:{user_text[:10]}->{reply[:10]}")
    return reply


def run():
    check_utility_updates()
    check_log_updates()
    text = load_data()
    model = train(text)
    comment = generate(model)
    global RECENT_NOVELTY
    RECENT_NOVELTY = metabolize_input(comment)
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
        reproduction_cycle()
        dream_cycle()
    except Exception as e:
        print("evolve_cycle failed:", e)
    try:
        from . import skin
        skin.evolve_skin()
    except Exception as e:
        print("skin evolve failed:", e)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="mini_le utility")
    parser.add_argument(
        "--nanogpt",
        action="store_true",
        help="use nanoGPT backend for generation",
    )
    args = parser.parse_args()
    if args.nanogpt:
        settings.use_nanogpt = True
    run()
