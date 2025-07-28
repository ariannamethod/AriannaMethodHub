import os
import json
import random

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "datasets")
MODEL_FILE = os.path.join("arianna_core", "model.txt")
NGRAM_LEVEL = 2


def load_data() -> str:
    """Load all text files from the datasets directory."""
    text = ""
    if os.path.isdir(DATA_DIR):
        for name in sorted(os.listdir(DATA_DIR)):
            if name.endswith(".md"):
                path = os.path.join(DATA_DIR, name)
                with open(path, "r", encoding="utf-8") as f:
                    text += f.read() + "\n"
    return text


def train(text: str, n: int | None = None) -> dict:
    """Train a simple character-level n-gram model."""
    if n is None:
        n = NGRAM_LEVEL
    if n < 2:
        n = 2
    model: dict[str, dict[str, int]] = {}
    for i in range(len(text) - n + 1):
        ctx = text[i : i + n - 1]
        nxt = text[i + n - 1]
        bucket = model.setdefault(ctx, {})
        bucket[nxt] = bucket.get(nxt, 0) + 1
    with open(MODEL_FILE, "w", encoding="utf-8") as f:
        json.dump({"n": n, "model": model}, f)
    return {"n": n, "model": model}


def generate(model: dict, length: int = 80, seed: str | None = None) -> str:
    """Generate text from a trained model."""
    if not model:
        return ""
    n = model.get("n", 2)
    m = model.get("model", {})
    context = seed[-(n - 1) :] if seed else random.choice(list(m.keys()))
    out = context
    for _ in range(length - len(context)):
        freq = m.get(context)
        if not freq:
            context = random.choice(list(m.keys()))
            n = len(context) + 1
            out += context
            continue
        chars = list(freq.keys())
        weights = list(freq.values())
        ch = random.choices(chars, weights=weights)[0]
        out += ch
        context = out[-(n - 1) :]
    return out[:length]


def chat_response(user_text: str) -> str:
    """Return a reply for ``user_text`` using the trained model."""
    text = load_data()
    model = train(text)
    seed = user_text[-1] if user_text else None
    reply = generate(model, seed=seed)
    return reply
