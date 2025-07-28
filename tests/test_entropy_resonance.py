from arianna_core import entropy_resonance
import time


def test_calculate_entropy_basic():
    assert entropy_resonance.calculate_entropy("aaaa") == 0.0
    value = entropy_resonance.calculate_entropy("abcd")
    assert value > 1.9


def test_resonance_check():
    assert not entropy_resonance.resonance_check(3.9)
    assert entropy_resonance.resonance_check(4.1)


def test_entropy_mutation_changes_model():
    model = {"n": 2, "model": {"a": {"b": 1}}}
    mutated = entropy_resonance.entropy_mutation(model, "ab")
    assert mutated["model"]["a"]["b"] > 1


def test_entropy_resonance_mutate(tmp_path, monkeypatch):
    model = {"n": 2, "model": {"a": {"b": 1}, "b": {"a": 1}}}
    monkeypatch.setattr(entropy_resonance.mini_le, "generate", lambda *a, **k: "abcdefghijklmnopqrstuvwxyz" * 2)
    log = tmp_path / "ent.log"
    monkeypatch.setattr(entropy_resonance, "LOG_FILE", str(log))
    mutated, ent, changed = entropy_resonance.entropy_resonance_mutate(model)
    assert ent > 0
    assert changed
    assert log.exists()


def test_entropy_resonance_mutate_performance(monkeypatch):
    model = {"n": 2, "model": {"a": {"b": 1}}}
    monkeypatch.setattr(entropy_resonance.mini_le, "generate", lambda *a, **k: "ab" * 50)
    start = time.time()
    entropy_resonance.entropy_resonance_mutate(model)
    assert time.time() - start < 0.5
