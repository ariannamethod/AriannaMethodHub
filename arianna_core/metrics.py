"""Utility metrics for text analysis."""
from __future__ import annotations

import math
from typing import Iterable

# Default set of affinity words used across modules
DEFAULT_AFFINITY_WORDS = ["resonance", "echo", "thunder", "love"]


def calculate_entropy(text: str) -> float:
    """Return the Shannon entropy of ``text``.

    The value is ``0.0`` for empty strings.
    """
    if not text:
        return 0.0
    freq = {c: text.count(c) / len(text) for c in set(text)}
    return -sum(p * math.log2(p) for p in freq.values())


def calculate_affinity(text: str, words: Iterable[str] | None = None) -> float:
    """Return the proportion of characters that belong to ``words``.

    ``words`` defaults to :data:`DEFAULT_AFFINITY_WORDS`.
    The value is ``0.0`` for empty strings.
    """
    if not text:
        return 0.0
    word_list = list(words) if words is not None else DEFAULT_AFFINITY_WORDS
    lower = text.lower()
    return sum(lower.count(w) for w in word_list) / len(text)
