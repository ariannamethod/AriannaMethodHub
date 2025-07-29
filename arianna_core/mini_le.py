import os
import json
import random
import gzip
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "datasets")
MODEL_FILE = os.path.join(os.path.dirname(__file__), "model.txt")
LOG_FILE = os.path.join(os.path.dirname(__file__), "log.txt")
HUMAN_LOG = os.path.join(os.path.dirname(__file__), "humanbridge.log")
LOG_MAX_BYTES = 1_000_000
LOG_KEEP = 3
NGRAM_LEVEL = 2
last_entropy: float = 0.0


def rotate_log(path: str, max_bytes: int = LOG_MAX_BYTES, keep: int = LOG_KEEP) -> None:
    """Archive ``path`` when it exceeds ``max_bytes`` and prune old archives."""
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
        [f for f in os.listdir(dir_path) if f.startswith(base) and f.endswith(".gz")],
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
        ctx = text[i : i + n - 1]
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
    context = seed[-(n - 1) :] if seed else rng.choice(list(m.keys()))
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
        context = output[-(n - 1) :]
    return output[:length]


def chat_response(message: str) -> str:
    """Return a generated reply to ``message`` using the saved model."""
    model = load_model()
    if model is None:
        model = train(load_data(), n=NGRAM_LEVEL)
    return generate(model, length=60, seed=message)


def reproduction_cycle(extra_logs: str | None = None) -> dict:
    """Retrain the model from datasets and logs and return the new model."""
    base = load_data()
    logs = extra_logs
    if logs is None:
        logs = ""
        for path in [LOG_FILE, HUMAN_LOG]:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    logs += f.read() + "\n"
    model = train(base + logs, n=NGRAM_LEVEL)
    return model
