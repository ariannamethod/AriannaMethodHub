import numpy as np
import pytest

from arianna_core.rag.hashed_vector import cosine, hashed_vector


def test_hashed_vector_deterministic():
    v1 = hashed_vector("Hello world", 32)
    v2 = hashed_vector("Hello world", 32)
    assert v1.shape == (32,)
    assert np.allclose(v1, v2)


def test_cosine_similarity():
    v1 = hashed_vector("hello", 16)
    v2 = hashed_vector("hello", 16)
    v3 = hashed_vector("world", 16)
    assert cosine(v1, v2) == pytest.approx(1.0)
    assert cosine(v1, v3) < 1.0
