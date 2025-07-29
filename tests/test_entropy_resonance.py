from arianna_core import entropy_resonance, mini_le


def test_entropy_resonance_log_rotation(tmp_path, monkeypatch):
    log = tmp_path / "entropy.log"
    monkeypatch.setattr(entropy_resonance, "LOG_FILE", str(log))
    monkeypatch.setattr(entropy_resonance, "LOG_MAX_BYTES", 10)
    model = {"n": 2, "model": {"a": {"a": 1}}}
    entropy_resonance.entropy_resonance_mutate(model)
    entropy_resonance.entropy_resonance_mutate(model)
    archives = list(tmp_path.glob("entropy.log.*.gz"))
    assert archives
    assert log.exists()
