import torch
import torch.nn as nn
import torch.nn.functional as F
from pathlib import Path
import random
import time

BASE_DIR = Path(__file__).resolve().parent
MODEL_FILE = BASE_DIR / "model.pth"
LOG_FILE = BASE_DIR / "responses.log"
DATA_FILES = [BASE_DIR.parent / "README.md", BASE_DIR.parent / "Arianna-Method-v2.9.md"]


def load_text():
    texts = []
    for f in DATA_FILES:
        if f.exists():
            texts.append(f.read_text(encoding="utf-8"))
    return "\n".join(texts)


def build_vocab(text: str):
    chars = sorted(list(set(text)))
    stoi = {ch: i for i, ch in enumerate(chars)}
    itos = {i: ch for ch, i in stoi.items()}
    return stoi, itos


class BigramModel(nn.Module):
    def __init__(self, vocab_size: int):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, vocab_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.embed(x)

    def generate(self, idx: torch.Tensor, max_new_tokens: int) -> torch.Tensor:
        for _ in range(max_new_tokens):
            logits = self(idx[:, -1])
            probs = F.softmax(logits, dim=-1)
            next_idx = torch.multinomial(probs, num_samples=1)
            idx = torch.cat((idx, next_idx), dim=1)
        return idx


def train_model(text: str, n_steps: int = 500) -> tuple:
    stoi, itos = build_vocab(text)
    vocab_size = len(stoi)
    data = torch.tensor([stoi[c] for c in text], dtype=torch.long)

    model = BigramModel(vocab_size)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-2)

    for _ in range(n_steps):
        ix = torch.randint(0, len(data) - 1, (32,))
        x = data[ix]
        y = data[ix + 1]
        logits = model(x)
        loss = F.cross_entropy(logits, y)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    torch.save({"model": model.state_dict(), "stoi": stoi, "itos": itos}, MODEL_FILE)
    return model, stoi, itos


def load_model():
    if not MODEL_FILE.exists():
        return None, None, None
    checkpoint = torch.load(MODEL_FILE)
    stoi = checkpoint["stoi"]
    itos = checkpoint["itos"]
    model = BigramModel(len(stoi))
    model.load_state_dict(checkpoint["model"])
    return model, stoi, itos


def get_log_text() -> str:
    if LOG_FILE.exists():
        return LOG_FILE.read_text(encoding="utf-8")
    return ""


def append_log(text: str) -> None:
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(text + "\n")


def generate_comment(max_tokens: int = 40) -> str:
    model, stoi, itos = load_model()
    if model is None:
        text = load_text()
        model, stoi, itos = train_model(text)

    log_text = get_log_text().strip()
    if log_text:
        start_char = log_text[-1]
    else:
        start_char = random.choice(list(stoi.keys()))

    idx = torch.tensor([[stoi.get(start_char, 0)]], dtype=torch.long)
    out_idx = model.generate(idx, max_tokens)
    out_text = "".join(itos[i] for i in out_idx[0].tolist())
    comment = out_text[len(start_char):].strip().split("\n")[0]
    append_log(comment)
    return comment
