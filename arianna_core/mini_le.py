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
NGRAM_LEVEL = 2


def rotate_log(path: str, max_bytes: int, keep: int = 3) -> None:
    """Archive ``path`` with a timestamp if it exceeds ``max_bytes``."""
    if not os.path.exists(path) or os.path.getsize(path) < max_bytes:
        return
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    archive = f"{path}.{ts}.gz"
    with open(path, "rb") as src, gzip.open(archive, "wb") as dst:
        dst.write(src.read())
    os.remove(path)
    base = os.path.basename(path)
    directory = os.path.dirname(path)
    archives = sorted(
        [f for f in os.listdir(directory) if f.startswith(base + ".")],
        reverse=True,
    )
    for old in archives[keep:]:
        try:
            os.remove(os.path.join(directory, old))
        except FileNotFoundError:
            pass


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
