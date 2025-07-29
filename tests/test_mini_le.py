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
    reply = mini_le.chat_response("a")
    assert isinstance(reply, str) and reply


def test_reproduction_cycle(tmp_path, monkeypatch):
    model_file = tmp_path / "model.txt"
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "d.txt").write_text("abcd", encoding="utf-8")
    log_file = tmp_path / "log.txt"
    log_file.write_text("xx", encoding="utf-8")
    human_log = tmp_path / "human.log"
    human_log.write_text("yy", encoding="utf-8")
    monkeypatch.setattr(mini_le, "MODEL_FILE", str(model_file))
    monkeypatch.setattr(mini_le, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(mini_le, "LOG_FILE", str(log_file))
    monkeypatch.setattr(mini_le, "HUMAN_LOG", str(human_log))
    model_file.write_text("old", encoding="utf-8")
    model = mini_le.reproduction_cycle()
    assert model_file.read_text(encoding="utf-8") != "old"
    assert isinstance(model, dict)
