import logging
import random

from .config import is_enabled
from .metrics import calculate_entropy, calculate_affinity
from .mini_le import get_mini_le, MiniLE

_le: MiniLE | None = None
MODEL_FILE: str = ""
LOG_FILE: str = ""
event_count = 0


def _load_refs():
    global _le, MODEL_FILE, LOG_FILE
    if _le is None:
        _le = get_mini_le()
        MODEL_FILE = _le.model_file
        LOG_FILE = _le.log_file
    assert _le is not None


def trigger_pain(output: str, max_ent: float = 8.0) -> float:
    """Calculate pain score and mutate the model when it is high."""
    if not is_enabled("pain"):
        logging.info("[pain] feature disabled, skipping")
        return 0.0
    _load_refs()
    from json import dump

    aff = calculate_affinity(output)
    ent = calculate_entropy(output)
    score = (1 - aff) * (max_ent - ent)
    if score > 0.5:
        model = _le.load_model()
        if model:
            m = model['model'] if 'model' in model else model
            for ctx in m:
                for ch, v in m[ctx].items():
                    m[ctx][ch] = max(1, int(v * random.uniform(0.8, 1.2)))
            with open(_le.model_file, 'w', encoding='utf-8') as f:
                dump(model, f)
        with open(_le.log_file, 'a', encoding='utf-8') as f:
            f.write(f"Pain event: score {score:.2f}, mutated.\n")
        global event_count
        event_count += 1
    return score


def check_once() -> None:
    """Run a single pain check if the feature is enabled."""
    if not is_enabled("pain"):
        logging.info("[pain] feature disabled, skipping")
        return
    _load_refs()
    model = _le.load_model()
    if model:
        out = _le.generate(model, length=20)
        trigger_pain(out)


if __name__ == '__main__':
    test_output = 'resonance echo thunder love' * 5
    trigger_pain(test_output)
