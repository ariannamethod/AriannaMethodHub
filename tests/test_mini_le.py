import json
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

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


def test_log_interaction_thread_safety(tmp_path, monkeypatch):
    log = tmp_path / "human.log"
    monkeypatch.setattr(mini_le, "HUMAN_LOG", str(log))
    monkeypatch.setattr(mini_le, "LOG_MAX_BYTES", 1_000_000)
    monkeypatch.setattr(mini_le, "rotate_log", lambda *a, **kw: None)

    threads = []
    for i in range(5):
        t = threading.Thread(
            target=mini_le.log_interaction,
            args=(f"u{i}", f"a{i}"),
            name=f"t{i}",
        )
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 5
    parts = {line.split(" ", 1)[1] for line in lines}
    expected = {f"USER:u{i} AI:a{i}" for i in range(5)}
    assert parts == expected


def test_run_thread_safety(tmp_path, monkeypatch):
    log = tmp_path / "log.txt"
    monkeypatch.setattr(mini_le, "LOG_FILE", str(log))
    monkeypatch.setattr(mini_le, "rotate_log", lambda *a, **kw: None)
    monkeypatch.setattr(mini_le, "update_index", lambda comment: None)
    monkeypatch.setattr(mini_le, "evolve", lambda entry: None)
    monkeypatch.setattr(mini_le, "load_data", lambda: "")
    monkeypatch.setattr(mini_le, "train", lambda text: {})
    monkeypatch.setattr(
        mini_le,
        "generate",
        lambda *a, **kw: f"cmt-{threading.get_ident()}",
    )

    threads = [threading.Thread(target=mini_le.run, name=f"r{i}") for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 5
    assert len(set(lines)) == 5
