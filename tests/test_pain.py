import json
from types import SimpleNamespace
from arianna_core import pain


def test_trigger_pain_mutates(tmp_path, monkeypatch):
    model_file = tmp_path / "model.txt"
    log_file = tmp_path / "log.txt"
    model = {"n": 2, "model": {"a": {"b": 10}}}
    model_file.write_text(json.dumps(model))
    pain._mini_le = SimpleNamespace(
        load_model=lambda: json.loads(model_file.read_text()),
        MODEL_FILE=str(model_file),
        LOG_FILE=str(log_file),
    )
    monkeypatch.setattr(pain.random, "uniform", lambda a, b: 1.2)
    score = pain.trigger_pain("zzz", max_ent=5.0)
    mutated = json.loads(model_file.read_text())
    assert mutated["model"]["a"]["b"] != 10
    assert "Pain event" in log_file.read_text()
    assert score > 0.5
