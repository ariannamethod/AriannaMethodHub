from arianna_core import mini_le


def test_metabolize_input_novelty(tmp_path, monkeypatch):
    model_file = tmp_path / "model.txt"
    monkeypatch.setattr(mini_le, "MODEL_FILE", str(model_file))
    mini_le.train("abcabc", n=2)
    novelty = mini_le.metabolize_input("def")
    assert novelty == 1.0


def test_immune_filter_blocks():
    mini_le.IMMUNE_BLOCKED = 0
    assert not mini_le.immune_filter("badword here")
    assert mini_le.IMMUNE_BLOCKED == 1
    assert mini_le.immune_filter("hello")


def test_reproduction_cycle(tmp_path, monkeypatch):
    model_file = tmp_path / "model.txt"
    repro_file = tmp_path / "repro.txt"
    monkeypatch.setattr(mini_le, "MODEL_FILE", str(model_file))
    monkeypatch.setattr(mini_le, "REPRO_FILE", str(repro_file))
    sample = tmp_path / "sample.txt"
    sample.write_text("abc", encoding="utf-8")
    monkeypatch.setattr(mini_le, "get_data_files", lambda: [str(sample)])
    model = mini_le.reproduction_cycle()
    assert model_file.exists()
    assert repro_file.exists()
    assert isinstance(model, dict)
