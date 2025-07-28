# ruff: noqa: E402
import json
import sqlite3
from arianna_core import mini_le  # noqa: E402


def test_train_writes_model(tmp_path, monkeypatch):
    model_file = tmp_path / "model.txt"
    monkeypatch.setattr(mini_le, "MODEL_FILE", str(model_file))
    model = mini_le.train("ababa", n=2)
    assert model == {"n": 2, "model": {"a": {"b": 2}, "b": {"a": 2}}}
    assert model_file.exists()
    content = json.loads(model_file.read_text(encoding="utf-8"))
    assert content == {"n": 2, "model": {"a": {"b": 2}, "b": {"a": 2}}}


def test_generate_cycle():
    model = {"n": 2, "model": {"a": {"b": 1}, "b": {"c": 1}, "c": {"a": 1}}}
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
    index = log.with_suffix(".log.index")
    assert index.exists()
    assert log.read_text(encoding="utf-8").endswith("AI:ok\n")


def test_evolve_appends_entry(tmp_path, monkeypatch):
    evo_file = tmp_path / "evolution_steps.py"
    monkeypatch.setattr(mini_le, "EVOLUTION_FILE", str(evo_file))
    mini_le.evolve("test")
    assert evo_file.exists()
    lines = evo_file.read_text(encoding="utf-8").splitlines()
    assert lines == [
        "evolution_steps = {'chat': [], 'ping': [], 'resonance': [], 'error': []}",
        "evolution_steps['error'].append('test')",
    ]


def test_search_logs(tmp_path, monkeypatch):
    log = tmp_path / "human.log"
    monkeypatch.setattr(mini_le, "HUMAN_LOG", str(log))
    monkeypatch.setattr(mini_le, "LOG_MAX_BYTES", 10)
    log.write_text("x" * 11)
    mini_le.log_interaction("foo", "bar")
    result = mini_le.search_logs("foo", str(log))
    assert any("foo" in r for r in result)


def test_record_pattern_and_health(tmp_path, monkeypatch):
    db = tmp_path / "mem.db"
    monkeypatch.setattr(mini_le, "MEMORY_DB", str(db))
    mini_le.record_pattern("hello")
    mini_le.record_pattern("hello")
    conn = sqlite3.connect(db)
    count = conn.execute("select count from patterns where pattern='hello'").fetchone()[0]
    conn.close()
    assert count == 2
    report = mini_le.health_report()
    assert isinstance(report, dict)


def test_chat_limit_grows_with_logs(tmp_path, monkeypatch):
    log = tmp_path / "human.log"
    monkeypatch.setattr(mini_le, "HUMAN_LOG", str(log))
    mini_le.CHAT_SESSION_COUNT = 0
    # no history -> limit should be 3
    resp1 = mini_le.chat_response("hi")
    assert resp1 != "MESSAGE LIMIT REACHED"
    for _ in range(mini_le._allowed_messages() - 1):
        mini_le.chat_response("x")
    assert mini_le.chat_response("extra") == "MESSAGE LIMIT REACHED"
    # add history to increase allowed messages
    log.write_text("line\n" * 20, encoding="utf-8")
    mini_le.CHAT_SESSION_COUNT = 0
    assert mini_le.chat_response("hi") != "MESSAGE LIMIT REACHED"


def mismatch(a: str, b: str) -> int:
    return sum(ch1 != ch2 for ch1, ch2 in zip(a, b))


def test_trigram_generation_closer_to_source(tmp_path, monkeypatch):
    text = "abcabcabc"
    model_file = tmp_path / "model.txt"
    monkeypatch.setattr(mini_le, "MODEL_FILE", str(model_file))

    bi = mini_le.train(text, n=2)
    tri = mini_le.train(text, n=3)

    gen_bi = mini_le.generate(bi, length=len(text), seed="ab")
    gen_tri = mini_le.generate(tri, length=len(text), seed="ab")

    assert mismatch(text, gen_tri) <= mismatch(text, gen_bi)

