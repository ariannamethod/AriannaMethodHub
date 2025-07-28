import math
import random
import importlib

_mini_le = None
MODEL_FILE = None
LOG_FILE = None

def _load_refs():
    global _mini_le, MODEL_FILE, LOG_FILE
    if _mini_le is None:
        _mini_le = importlib.import_module("arianna_core.mini_le")
        MODEL_FILE = _mini_le.MODEL_FILE
        LOG_FILE = _mini_le.LOG_FILE

WORDS = ['resonance', 'echo', 'thunder', 'love']

def calculate_affinity(output: str) -> float:
    if not output:
        return 0.0
    return sum(output.lower().count(w) for w in WORDS) / len(output)

def calculate_entropy(output: str) -> float:
    if not output:
        return 0.0
    freq = {c: output.count(c) / len(output) for c in set(output)}
    return -sum(p * math.log2(p) for p in freq.values())

def trigger_pain(output: str, max_ent: float = 8.0) -> float:
    """Calculate pain score and mutate the model when it is high."""
    _load_refs()
    from json import dump

    aff = calculate_affinity(output)
    ent = calculate_entropy(output)
    score = (1 - aff) * (max_ent - ent)
    if score > 0.5:
        model = _mini_le.load_model()
        if model:
            m = model['model'] if 'model' in model else model
            for ctx in m:
                for ch, v in m[ctx].items():
                    m[ctx][ch] = max(1, int(v * random.uniform(0.8, 1.2)))
            with open(_mini_le.MODEL_FILE, 'w', encoding='utf-8') as f:
                dump(model, f)
        with open(_mini_le.LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"Pain event: score {score:.2f}, mutated.\n")
    return score

if __name__ == '__main__':
    test_output = 'resonance echo thunder love' * 5
    trigger_pain(test_output)
