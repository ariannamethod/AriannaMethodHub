import json
from arianna_core import mini_le  # noqa: E402


def test_train_writes_model(tmp_path, monkeypatch):
    model_file = tmp_path / "model.txt"
    monkeypatch.setattr(mini_le, "MODEL_FILE", str(model_file))
    model = mini_le.train("ababa")
    assert model == {"a": {"b": 2}, "b": {"a": 2}}
    assert model_file.exists()
    content = json.loads(model_file.read_text(encoding="utf-8"))
    assert content == {"a": {"b": 2}, "b": {"a": 2}}


def test_generate_cycle():
    model = {"a": {"b": 1}, "b": {"c": 1}, "c": {"a": 1}}
    result = mini_le.generate(model, length=4, seed="a")
    assert result == "abca"


def test_log_rotation(tmp_path, monkeypatch):
    log = tmp_path / "human.log"
    monkeypatch.setattr(mini_le, "HUMAN_LOG", str(log))
    monkeypatch.setattr(mini_le, "LOG_MAX_BYTES", 10)
    log.write_text("x" * 11)
    mini_le.log_interaction("hi", "ok")
    rotated = list(tmp_path.glob("human.log.*"))
    assert len(rotated) == 1
    assert log.read_text(encoding="utf-8").endswith("AI:ok\n")
