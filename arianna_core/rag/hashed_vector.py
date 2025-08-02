"""Utilities for hashed text vectors."""

from __future__ import annotations

import hashlib
import re

import numpy as np

_TOKEN_RE = re.compile(r"\w+")


def _stable_hash(token: str) -> int:
    """Return a stable integer hash for ``token``."""
    digest = hashlib.sha1(token.encode("utf-8")).hexdigest()
    return int(digest, 16)


def hashed_vector(text: str, dim: int) -> np.ndarray:
    """Return a normalized hashed vector for ``text``.

    Parameters
    ----------
    text:
        Input text to vectorize.
    dim:
        Dimensionality of the output vector.
    """

    vec = np.zeros(dim, dtype=np.float32)
    for token in _TOKEN_RE.findall(text.lower()):
        idx = _stable_hash(token) % dim
        vec[idx] += 1.0
    norm = np.linalg.norm(vec)
    if norm:
        vec /= norm
    return vec


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Return cosine similarity between vectors ``a`` and ``b``."""
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


__all__ = ["hashed_vector", "cosine"]
