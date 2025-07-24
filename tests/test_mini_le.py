import json
import sys
from pathlib import Path
import threading
import itertools

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


def test_concurrent_log_interaction(tmp_path, monkeypatch):
    log = tmp_path / "human.log"
    monkeypatch.setattr(mini_le, "HUMAN_LOG", str(log))

    def worker(i: int) -> None:
        mini_le.log_interaction(f"u{i}", f"a{i}")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 5
    msgs = {line.split(" ", 1)[1] for line in lines}
    expected = {f"USER:u{i} AI:a{i}" for i in range(5)}
    assert msgs == expected


def test_concurrent_run(tmp_path, monkeypatch):
    log = tmp_path / "log.txt"
    monkeypatch.setattr(mini_le, "LOG_FILE", str(log))
    monkeypatch.setattr(mini_le, "DATA_FILES", [])
    monkeypatch.setattr(mini_le, "MODEL_FILE", str(tmp_path / "model.txt"))
    monkeypatch.setattr(mini_le, "HUMAN_LOG", str(tmp_path / "human.log"))
    monkeypatch.setattr(mini_le, "update_index", lambda comment: None)
    monkeypatch.setattr(mini_le, "evolve", lambda entry: None)
    monkeypatch.setattr(mini_le, "load_data", lambda: "")

    counter = itertools.count()

    def fake_train(text: str) -> dict:
        return {}

    def fake_generate(model, length=80, seed=None):
        return f"c{next(counter)}"

    monkeypatch.setattr(mini_le, "train", fake_train)
    monkeypatch.setattr(mini_le, "generate", fake_generate)

    threads = [threading.Thread(target=mini_le.run) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 5
    comments = {line.split(" ", 1)[1] for line in lines}
    assert comments == {f"c{i}" for i in range(5)}
