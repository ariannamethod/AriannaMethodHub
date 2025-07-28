# ruff: noqa: E402
import json
from arianna_core import mini_le  # noqa: E402
from arianna_core import memory, health  # noqa: E402


def test_train_writes_model(tmp_path, monkeypatch):
    model_file = tmp_path / "model.txt"
    monkeypatch.setattr(mini_le, "MODEL_FILE", str(model_file))
    model = mini_le.train("ababa")
    assert model == {"a": {"b": 2}, "b": {"a": 2}}
    assert model_file.exists()
    content = json.loads(model_file.read_text(encoding="utf-8"))
    assert content == {"a": {"b": 2}, "b": {"a": 2}}


def test_train_bigram(tmp_path, monkeypatch):
    model_file = tmp_path / "model.txt"
    monkeypatch.setattr(mini_le, "MODEL_FILE", str(model_file))
    model = mini_le.train("ababa", n=2)
    assert model == {"ab": {"a": 2}, "ba": {"b": 1}}


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
    rotated = list(tmp_path.glob("human.log.*.gz"))
    assert len(rotated) == 1
    index = tmp_path / "human.log.index"
    assert index.exists()
    assert log.read_text(encoding="utf-8").endswith("AI:ok\n")


def test_evolve_appends_entry(tmp_path, monkeypatch):
    evo_file = tmp_path / "evolution_steps.py"
    metrics = tmp_path / "metrics.json"
    monkeypatch.setattr(mini_le, "EVOLUTION_FILE", str(evo_file))
    monkeypatch.setattr(mini_le, "EVOLUTION_METRICS", str(metrics))
    mini_le.evolve("chat:test")
    assert evo_file.exists()
    lines = evo_file.read_text(encoding="utf-8").splitlines()
    assert lines == [
        "evolution_steps = []",
        "evolution_steps.append('chat:test')",
    ]
    data = json.loads(metrics.read_text(encoding="utf-8"))
    assert data["chat"] == 1


def test_memory_updates(tmp_path, monkeypatch):
    db = tmp_path / "mem.db"
    monkeypatch.setattr(memory, "DB_PATH", str(db))
    model = {"a": {"b": 2}, "b": {"a": 2}}
    memory.update_patterns(model, db_path=str(db))
    rows = memory.top_patterns(db_path=str(db))
    assert rows[0][0] in {"a", "b"}


def test_health_status(tmp_path, monkeypatch):
    monkeypatch.setattr(mini_le, "MODEL_FILE", str(tmp_path / "m.txt"))
    stats = health.health_status()
    assert "model_exists" in stats
