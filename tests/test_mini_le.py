# ruff: noqa: E402
import json
import sqlite3
import random
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


def test_generate_deterministic_with_rng():
    model = {"n": 2, "model": {"a": {"b": 1}, "b": {"c": 1}, "c": {"a": 1}}}
    rng1 = random.Random(42)
    rng2 = random.Random(42)
    out1 = mini_le.generate(model, length=6, seed="a", rng=rng1)
    out2 = mini_le.generate(model, length=6, seed="a", rng=rng2)
    assert out1 == out2


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


def test_adaptive_ngram(tmp_path, monkeypatch):
    model_file = tmp_path / "model.txt"
    monkeypatch.setattr(mini_le, "MODEL_FILE", str(model_file))
    long_text = "abc" * 4000  # > 10000 chars
    model = mini_le.train(long_text, n=None)
    assert model["n"] >= 3


def test_dream_cycle(monkeypatch):
    calls = {}

    monkeypatch.setattr(mini_le, "load_data", lambda: "abc")
    monkeypatch.setattr(mini_le, "train", lambda t: {"n": 2, "model": {}})
    monkeypatch.setattr(mini_le, "generate", lambda m: "dream")
    monkeypatch.setattr(mini_le, "log_interaction", lambda u, a: calls.setdefault("log", True))
    monkeypatch.setattr(mini_le, "record_pattern", lambda p: calls.setdefault("rec", True))
    monkeypatch.setattr(mini_le, "reproduction_cycle", lambda: calls.setdefault("repro", True))

    mini_le.dream_cycle()
    assert calls == {"log": True, "rec": True, "repro": True}


def test_resonance_metrics(tmp_path, monkeypatch):
    db = tmp_path / "mem.db"
    monkeypatch.setattr(mini_le, "MEMORY_DB", str(db))
    mini_le.record_pattern("a")
    mini_le.record_pattern("a")
    mini_le.record_pattern("b")
    metrics = mini_le.resonance_metrics()
    assert metrics["total"] == 3
    assert metrics["top"].get("a") > metrics["top"].get("b", 0)


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


def _patch_chat(monkeypatch):
    monkeypatch.setattr(mini_le, "check_utility_updates", lambda: None)
    monkeypatch.setattr(mini_le, "_allowed_messages", lambda: 10)
    monkeypatch.setattr(mini_le, "immune_filter", lambda t: True)
    monkeypatch.setattr(mini_le, "load_data", lambda: "")
    monkeypatch.setattr(mini_le, "train", lambda t: {})
    monkeypatch.setattr(mini_le, "log_interaction", lambda *a, **k: None)
    monkeypatch.setattr(mini_le, "record_pattern", lambda *a, **k: None)
    monkeypatch.setattr(mini_le, "evolve", lambda *a, **k: None)
    monkeypatch.setattr(mini_le, "metabolize_input", lambda t, n=None: 0)


def test_chat_response_uses_nanogpt(monkeypatch):
    calls = {}

    def fake_nano(*args, **kwargs):
        calls["nano"] = True
        return "nano"

    def fake_generate(*args, **kwargs):
        calls["generate"] = True
        return "ngram"

    _patch_chat(monkeypatch)
    monkeypatch.setattr(mini_le.nanogpt_bridge, "generate", fake_nano)
    monkeypatch.setattr(mini_le, "generate", fake_generate)
    mini_le.CHAT_SESSION_COUNT = 0
    reply = mini_le.chat_response("hi", use_nanogpt=True)
    assert reply == "nano"
    assert calls.get("nano") and "generate" not in calls


def test_chat_response_nanogpt_fallback(monkeypatch):
    calls = {}

    def fake_nano(*args, **kwargs):
        calls["nano"] = True
        return None

    def fake_generate(*args, **kwargs):
        calls["generate"] = True
        return "fallback"

    _patch_chat(monkeypatch)
    monkeypatch.setattr(mini_le.nanogpt_bridge, "generate", fake_nano)
    monkeypatch.setattr(mini_le, "generate", fake_generate)
    mini_le.CHAT_SESSION_COUNT = 0
    reply = mini_le.chat_response("hi", use_nanogpt=True)
    assert reply == "fallback"
    assert calls.get("nano") and calls.get("generate")


def test_backoff_threshold(tmp_path):
    model = {"n": 2, "model": {"a": {"b": 1}}}
    rng = random.Random(1)
    out = mini_le.generate(model, length=4, seed="a", rng=rng, backoff_threshold=2)
    assert out == "aba"

