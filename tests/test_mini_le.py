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


def test_rotate_log_creates_archive(tmp_path, monkeypatch):
    log = tmp_path / "log.txt"
    monkeypatch.setattr(mini_le, "LOG_MAX_BYTES", 10)
    log.write_text("x" * 20, encoding="utf-8")
    mini_le.rotate_log(str(log), mini_le.LOG_MAX_BYTES)
    archives = list(tmp_path.glob("log.txt.*.gz"))
    assert len(archives) == 1
    assert not log.exists()
