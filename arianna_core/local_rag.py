try:
    import regex as re  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    import re
from functools import lru_cache
from typing import List, Tuple

_TOKEN_RE = re.compile(r"\b\w+\b")


def _tokenize(text: str) -> List[str]:
    """Return a list of lowercase words."""
    return _TOKEN_RE.findall(text.lower())


@lru_cache(maxsize=128)
def _vectorize_cached(text: str) -> dict:
    """Return cached vector representation for ``text``."""
    return _vectorize(_tokenize(text))


def _vectorize(tokens: List[str]) -> dict:
    vec = {}
    for t in tokens:
        vec[t] = vec.get(t, 0) + 1
    return vec


def _dot(v1: dict, v2: dict) -> float:
    return sum(v1.get(k, 0) * v2.get(k, 0) for k in v1)


class SimpleSearch:
    """Lightweight in-memory search over text snippets."""

    def __init__(self, snippets: List[str]):
        self.snippets = snippets
        # Pre-compute and store token vectors keyed by snippet text
        self.vectors = {s: _vectorize(_tokenize(s)) for s in snippets}

    def query(self, text: str, top_k: int = 3) -> List[str]:
        qvec = _vectorize_cached(text)
        scored: List[Tuple[str, float]] = [
            (snippet, _dot(self.vectors[snippet], qvec))
            for snippet in self.snippets
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [s for s, score in scored[:top_k] if score > 0]


def load_snippets(paths: List[str]) -> List[str]:
    """Load documents and split into paragraphs."""
    snippets: List[str] = []
    for path in paths:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        for para in text.split("\n\n"):
            para = para.strip()
            if para:
                snippets.append(para)
    return snippets

