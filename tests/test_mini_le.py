from arianna_core import mini_le


def test_train_and_generate(tmp_path, monkeypatch):
    model_file = tmp_path / "model.txt"
    monkeypatch.setattr(mini_le, "MODEL_FILE", str(model_file))
    model = mini_le.train("abba", n=2)
    assert model_file.exists()
    out = mini_le.generate(model, length=4, seed="a")
    assert out


def test_load_data(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "f.txt").write_text("abc", encoding="utf-8")
    monkeypatch.setattr(mini_le, "DATA_DIR", str(data_dir))
    text = mini_le.load_data()
    assert "abc" in text


def test_chat_response(tmp_path, monkeypatch):
    model_file = tmp_path / "model.txt"
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "f.txt").write_text("abcabc", encoding="utf-8")
    monkeypatch.setattr(mini_le, "MODEL_FILE", str(model_file))
    monkeypatch.setattr(mini_le, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(mini_le.settings, "n_gram_level", 2)
    reply = mini_le.chat_response("a")
    assert isinstance(reply, str) and reply


def test_reproduction_and_report(tmp_path, monkeypatch):
    model_file = tmp_path / "model.txt"
    data_dir = tmp_path / "data"
    db_file = tmp_path / "memory.db"
    repro_file = tmp_path / "last.txt"
    data_dir.mkdir()
    (data_dir / "d.txt").write_text("abcd" * 3, encoding="utf-8")
    monkeypatch.setattr(mini_le, "MODEL_FILE", str(model_file))
    monkeypatch.setattr(mini_le, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(mini_le, "DB_FILE", str(db_file))
    monkeypatch.setattr(mini_le, "LAST_REPRO_FILE", str(repro_file))
    monkeypatch.setattr(mini_le.settings, "n_gram_level", 2)
    mini_le.reproduction_cycle(threshold=1, max_rows=10)
    assert db_file.exists()
    report = mini_le.health_report()
    assert report["model_size"] > 0
    assert report["pattern_memory"] > 0
    assert report["last_reproduction"]


def test_metabolize_and_filter(tmp_path, monkeypatch):
    db_file = tmp_path / "memory.db"
    monkeypatch.setattr(mini_le, "DB_FILE", str(db_file))
    mini_le.update_pattern_memory("abab", n=2)
    assert mini_le.metabolize_input("abab", n=2) == 0.0
    assert mini_le.metabolize_input("zzzz", n=2) > 0.0
    mini_le.blocked_messages = 0
    assert mini_le.immune_filter("badword") == ""
    assert mini_le.blocked_messages == 1


def test_rotate_log(tmp_path, monkeypatch):
    log = tmp_path / "log.txt"
    log.write_bytes(b"x" * 10)
    mini_le.rotate_log(str(log), max_bytes=1, keep=2)
    archives = list(tmp_path.glob("log.txt.*.gz"))
    assert not log.exists()
    assert len(archives) == 1
    # rotate twice more to trigger pruning
    for i in range(2):
        new_log = tmp_path / "log.txt"
        new_log.write_bytes(b"y" * 10)
        mini_le.rotate_log(str(new_log), max_bytes=1, keep=2)
    archives = list(tmp_path.glob("log.txt.*.gz"))
    assert len(archives) <= 2
