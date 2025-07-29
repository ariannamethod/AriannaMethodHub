import json
import random
import os
import importlib
from datetime import datetime, timedelta
import logging
from typing import Any
from arianna_core.pain import (
    calculate_entropy,
    calculate_affinity,
    trigger_pain,
)
from .config import is_enabled

_mini_le: Any = None
MODEL_FILE: str = ""
LOG_FILE: str = ""


def _load_refs():
    global _mini_le, MODEL_FILE, LOG_FILE
    if _mini_le is None:
        _mini_le = importlib.import_module("arianna_core.mini_le")
        MODEL_FILE = _mini_le.MODEL_FILE
        LOG_FILE = _mini_le.LOG_FILE
    assert _mini_le is not None


def lorenz_distort(
    x: float,
    sigma: float = 10,
    rho: float = 28,
    beta: float = 8 / 3,
    dt: float = 0.01,
) -> float:
    y, _ = random.random(), random.random()
    dx = sigma * (y - x) * dt
    return x + dx


def predict_next(model: dict | None = None) -> str:
    """Generate a prediction sample if the feature is enabled."""
    if not is_enabled("sixth_sense"):
        logging.info("[sixth_sense] feature disabled, skipping")
        return ""
    _load_refs()
    if model is None:
        model = _mini_le.load_model()
    if not model:
        return ""
    m = model["model"] if "model" in model else model
    perturbed = {
        k: {ch: max(1, int(v * lorenz_distort(v))) for ch, v in freq.items()}
        for k, freq in m.items()
    }
    struct = {"n": model.get("n", 2), "model": perturbed}
    pred = _mini_le.generate(struct, length=100)
    with open(_mini_le.LOG_FILE, "a", encoding="utf-8") as f:
        f.write(
            f"{datetime.now().isoformat()} Prediction: {pred[:50]}... ent="
            f"{calculate_entropy(pred):.2f}\n"
        )
    return pred


def check_prediction(actual_output: str) -> None:
    if not is_enabled("sixth_sense"):
        logging.info("[sixth_sense] feature disabled, skipping")
        return
    _load_refs()
    if not os.path.exists(_mini_le.LOG_FILE):
        return
    with open(_mini_le.LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    preds = [line for line in lines if "Prediction:" in line]
    if not preds:
        return
    last = preds[-1]
    ts_str = last.split(" ")[0]
    try:
        pred_time = datetime.fromisoformat(ts_str)
    except ValueError:
        return
    if datetime.now() - pred_time <= timedelta(hours=24):
        return
    pred_ent = float(last.split("ent=")[1])
    pred_text = last.split("Prediction: ")[1].split("...")[0]
    pred_aff = calculate_affinity(pred_text)
    actual_ent = calculate_entropy(actual_output)
    actual_aff = calculate_affinity(actual_output)
    delta = abs(pred_ent - actual_ent) + abs(pred_aff - actual_aff)
    if delta < 0.5:
        model = _mini_le.load_model()
        if not model:
            return
        m = model["model"] if "model" in model else model
        for ctx in m:
            for ch in m[ctx]:
                m[ctx][ch] += 1
        with open(_mini_le.MODEL_FILE, "w", encoding="utf-8") as f:
            json.dump(model, f)
        with open(_mini_le.LOG_FILE, "a", encoding="utf-8") as f:
            f.write("Prediction match: boosted.\n")
    else:
        trigger_pain(actual_output)
        with open(_mini_le.LOG_FILE, "a", encoding="utf-8") as f:
            f.write(
                f"Prediction mismatch: delta {delta:.2f}, pain triggered.\n"
            )


if __name__ == "__main__":
    _load_refs()
    model = _mini_le.load_model() or {}
    pred = predict_next(model)
    check_prediction("sim actual output resonance")
