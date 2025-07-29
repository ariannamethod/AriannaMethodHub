import json
import math
from datetime import datetime
import logging

from . import mini_le
from .mini_le import rotate_log, LOG_MAX_BYTES
from .config import is_enabled

LOG_FILE = "arianna_core/entropy.log"


def calculate_entropy(text: str) -> float:
    """Return Shannon entropy of ``text``."""
    if not text:
        return 0.0
    freq = {c: text.count(c) / len(text) for c in set(text)}
    return -sum(p * math.log2(p) for p in freq.values())


def resonance_check(entropy: float, threshold: float = 4.0) -> bool:
    """Return ``True`` if ``entropy`` exceeds ``threshold``."""
    return entropy > threshold


def entropy_mutation(model: dict, sample: str) -> dict:
    """Boost model frequencies for characters present in ``sample``."""
    if not model:
        return model
    mutated = json.loads(json.dumps(model))
    data = mutated["model"] if "model" in mutated else mutated
    for ch in set(sample):
        for ctx in data.values():
            if ch in ctx:
                ctx[ch] += 1
    return mutated


def entropy_resonance_mutate(model: dict) -> tuple[dict, float, bool]:
    """Mutate ``model`` based on entropy of a generated sample."""
    sample = mini_le.generate(model, length=100)
    ent = calculate_entropy(sample)
    mutated = model
    changed = False
    if resonance_check(ent):
        mutated = entropy_mutation(model, sample)
        changed = mutated != model
    rotate_log(LOG_FILE, LOG_MAX_BYTES)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(
            f"{datetime.utcnow().isoformat()} entropy={ent:.2f} changed={changed}\n"
        )
    return mutated, ent, changed


def run_once() -> None:
    """Perform an entropy resonance cycle once if the feature is enabled."""
    if not is_enabled("entropy"):
        logging.info("[entropy] feature disabled, skipping")
        return
    model = mini_le.load_model() or {}
    mutated, ent, changed = entropy_resonance_mutate(model)
    mini_le.last_entropy = ent
    if changed:
        with open(mini_le.MODEL_FILE, "w", encoding="utf-8") as f:
            json.dump(mutated, f)
