import os
import json
import random
import gzip
import sqlite3
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "datasets")
MODEL_FILE = os.path.join(os.path.dirname(__file__), "model.txt")
LOG_FILE = os.path.join(os.path.dirname(__file__), "log.txt")
HUMAN_LOG = os.path.join(os.path.dirname(__file__), "humanbridge.log")
LOG_MAX_BYTES = 1_000_000
LOG_KEEP = 3
NGRAM_LEVEL = 2
last_entropy: float = 0.0
DB_FILE = os.path.join(os.path.dirname(__file__), "memory.db")
LAST_REPRO_FILE = os.path.join(os.path.dirname(__file__), "last_reproduction.txt")
BAD_WORDS = {"badword", "curse"}
blocked_messages = 0
last_novelty = 0.0


def rotate_log(
    path: str, max_bytes: int = LOG_MAX_BYTES, keep: int = LOG_KEEP
) -> None:
    """Archive ``path`` when it exceeds ``max_bytes`` and prune old
    archives."""
    if not os.path.exists(path) or os.path.getsize(path) < max_bytes:
        return
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    archive = f"{path}.{ts}.gz"
    with open(path, "rb") as src, gzip.open(archive, "wb") as dst:
        dst.write(src.read())
    os.remove(path)

    base = os.path.basename(path)
    dir_path = os.path.dirname(path)
    archives = sorted(
        [
            f
            for f in os.listdir(dir_path)
            if f.startswith(base) and f.endswith(".gz")
        ],
        reverse=True,
    )
    for old in archives[keep:]:
        os.remove(os.path.join(dir_path, old))


def load_data() -> str:
    """Return concatenated text from files in ``DATA_DIR``."""
    chunks = []
    if os.path.isdir(DATA_DIR):
        for name in os.listdir(DATA_DIR):
            path = os.path.join(DATA_DIR, name)
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    chunks.append(f.read())
    return "\n".join(chunks)


def train(text: str, n: int = NGRAM_LEVEL) -> dict:
    """Train an n-gram model from ``text`` and write it to ``MODEL_FILE``."""
    model: dict[str, dict[str, int]] = {}
    for i in range(len(text) - n + 1):
        ctx = text[i:i + n - 1]
        ch = text[i + n - 1]
        freq = model.setdefault(ctx, {})
        freq[ch] = freq.get(ch, 0) + 1
    data = {"n": n, "model": model}
    with open(MODEL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return data


def load_model() -> dict | None:
    if not os.path.exists(MODEL_FILE):
        return None
    with open(MODEL_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def generate(model: dict, length: int = 80, seed: str | None = None) -> str:
    """Generate ``length`` characters from ``model``."""
    if not model:
        return ""
    n = model.get("n", 2)
    m = model.get("model", {})
    rng = random
    if not m:
        return ""
    context = seed[-(n - 1):] if seed else rng.choice(list(m.keys()))
    output = context
    for _ in range(length - len(context)):
        freq = m.get(context)
        if not freq:
            context = rng.choice(list(m.keys()))
            output += context
            if len(output) >= length:
                break
            continue
        chars = list(freq.keys())
        weights = list(freq.values())
        ch = rng.choices(chars, weights=weights)[0]
        output += ch
        context = output[-(n - 1):]
    return output[:length]


def chat_response(message: str) -> str:
    """Return a generated reply to ``message`` using the saved model."""
    model = load_model()
    if model is None:
        model = train(load_data(), n=NGRAM_LEVEL)
    return generate(model, length=60, seed=message)


def _init_db() -> sqlite3.Connection:
    """Return a connection to the pattern memory database."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS patterns (pattern TEXT PRIMARY KEY, count INTEGER)"
    )
    return conn


def update_pattern_memory(text: str, n: int = NGRAM_LEVEL) -> None:
    """Add n-gram patterns from ``text`` to ``memory.db``."""
    conn = _init_db()
    rows = []
    for i in range(len(text) - n + 1):
        rows.append(text[i : i + n])
    with conn:
        for pat in rows:
            conn.execute(
                "INSERT INTO patterns(pattern, count) VALUES(?,1) "
                "ON CONFLICT(pattern) DO UPDATE SET count = count + 1",
                (pat,),
            )
    conn.close()


def maintain_pattern_memory(threshold: int = 1, max_rows: int = 1000) -> None:
    """Prune low-frequency patterns and cap table size."""
    conn = _init_db()
    with conn:
        conn.execute("DELETE FROM patterns WHERE count < ?", (threshold,))
        cur = conn.execute(
            "SELECT pattern, count FROM patterns ORDER BY count DESC"
        )
        rows = cur.fetchall()
        if len(rows) > max_rows:
            for pat, _ in rows[max_rows:]:
                conn.execute("DELETE FROM patterns WHERE pattern = ?", (pat,))
    conn.close()


def metabolize_input(text: str, n: int = NGRAM_LEVEL) -> float:
    """Return novelty score between 0 and 1 for ``text``."""
    global last_novelty
    conn = _init_db()
    unseen = 0
    total = 0
    for i in range(len(text) - n + 1):
        pat = text[i : i + n]
        total += 1
        cur = conn.execute(
            "SELECT 1 FROM patterns WHERE pattern = ? LIMIT 1", (pat,)
        )
        if cur.fetchone() is None:
            unseen += 1
    conn.close()
    score = unseen / total if total else 0.0
    last_novelty = score
    return score


def immune_filter(text: str) -> str:
    """Return ``""`` if ``text`` contains banned words."""
    global blocked_messages
    tokens = [t.lower() for t in text.split()]
    if any(t in BAD_WORDS for t in tokens):
        blocked_messages += 1
        return ""
    return text


def adaptive_mutation(model: dict) -> dict:
    """Randomly tweak model weights if novelty improves."""
    if not model or not model.get("model"):
        return model
    before = generate(model, length=40)
    score_before = metabolize_input(before)
    ctx = random.choice(list(model["model"].keys()))
    freq = model["model"][ctx]
    ch = random.choice(list(freq.keys()))
    old = freq[ch]
    freq[ch] = max(1, old + random.choice([-1, 1]))
    after = generate(model, length=40)
    score_after = metabolize_input(after)
    if score_after < score_before:
        freq[ch] = old
    return model


def reproduction_cycle(threshold: int = 1, max_rows: int = 1000) -> dict:
    """Retrain model, update memory and apply mutation."""
    text = load_data()
    model = train(text, n=NGRAM_LEVEL)
    update_pattern_memory(text)
    maintain_pattern_memory(threshold=threshold, max_rows=max_rows)
    model = adaptive_mutation(model)
    ts = datetime.utcnow().isoformat()
    with open(LAST_REPRO_FILE, "w", encoding="utf-8") as f:
        f.write(ts)
    return model


def health_report() -> dict:
    """Return health metrics about the system."""
    conn = _init_db()
    cur = conn.execute("SELECT COUNT(*) FROM patterns")
    mem_rows = cur.fetchone()[0]
    conn.close()
    model = load_model()
    model_size = len(model.get("model", {})) if model else 0
    last_rep = None
    if os.path.exists(LAST_REPRO_FILE):
        with open(LAST_REPRO_FILE, "r", encoding="utf-8") as f:
            last_rep = f.read().strip()
    return {
        "model_size": model_size,
        "pattern_memory": mem_rows,
        "blocked_messages": blocked_messages,
        "novelty": last_novelty,
        "last_reproduction": last_rep,
    }
