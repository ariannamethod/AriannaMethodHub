import math
import pytest

from arianna_core import entropy_resonance, metrics, pain, skin


def test_calculate_entropy_basic() -> None:
    text = "aaaab"
    expected = -(0.8 * math.log2(0.8) + 0.2 * math.log2(0.2))
    assert metrics.calculate_entropy(text) == pytest.approx(expected)


def test_calculate_affinity_default_and_custom() -> None:
    text = "resonance echo"
    assert metrics.calculate_affinity(text) == pytest.approx(2 / len(text))
    assert metrics.calculate_affinity(text, ["resonance"]) == pytest.approx(
        1 / len(text)
    )


def test_modules_use_shared_metrics() -> None:
    assert entropy_resonance.calculate_entropy is metrics.calculate_entropy
    assert pain.calculate_entropy is metrics.calculate_entropy
    assert pain.calculate_affinity is metrics.calculate_affinity
    assert skin.calculate_entropy is metrics.calculate_entropy
    assert skin.calculate_affinity is metrics.calculate_affinity
