import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "arianna-core"))

import mini_le  # type: ignore  # noqa: E402


def test_train_writes_model(tmp_path, monkeypatch):
    model_file = tmp_path / "model.txt"
    monkeypatch.setattr(mini_le, "MODEL_FILE", str(model_file))
    model = mini_le.train("ababa")
    assert model == {"a": {"b": 2}, "b": {"a": 2}}
    assert model_file.exists()
    content = model_file.read_text(encoding="utf-8").splitlines()
    assert "a\tb:2" in content
    assert "b\ta:2" in content


def test_generate_cycle():
    model = {"a": {"b": 1}, "b": {"c": 1}, "c": {"a": 1}}
    result = mini_le.generate(model, length=4, seed="a")
    assert result == "abca"
