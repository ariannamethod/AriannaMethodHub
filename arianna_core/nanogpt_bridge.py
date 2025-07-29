import os
import importlib
from typing import Optional

_MODEL = None

MODEL_PATH = os.path.join(os.path.dirname(__file__), "nanogpt.pt")


def load_model(path: str = MODEL_PATH):
    """Return a loaded NanoGPT model or ``None`` if unavailable."""
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    try:
        torch = importlib.import_module("torch")
    except ModuleNotFoundError:
        return None
    if not hasattr(torch, "load") or not path:
        return None
    try:
        model = torch.load(path, map_location="cpu")
        model.eval()
    except Exception:
        return None
    _MODEL = model
    return _MODEL


def generate(prompt: str, max_new_tokens: int = 80) -> Optional[str]:
    """Return NanoGPT output or ``None`` if generation fails."""
    model = load_model()
    if model is None:
        return None
    gen = getattr(model, "generate", None)
    if gen is None:
        return None
    try:
        return gen(prompt, max_new_tokens=max_new_tokens)
    except Exception:
        return None
