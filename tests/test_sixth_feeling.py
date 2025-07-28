import json
from types import SimpleNamespace
from arianna_core import sixth_feeling


def test_predict_next_logs(tmp_path, monkeypatch):
    log = tmp_path / "log.txt"
    model = {"n": 2, "model": {"a": {"b": 1}}}
    sixth_feeling._mini_le = SimpleNamespace(
        LOG_FILE=str(log),
        MODEL_FILE=str(log),
        generate=lambda *a, **k: "ab",
        load_model=lambda: model,
    )
    sixth_feeling.LOG_FILE = str(log)
    sixth_feeling.MODEL_FILE = str(log)
    pred = sixth_feeling.predict_next(model)
    assert pred == "ab"
    assert "Prediction:" in log.read_text()


def test_check_prediction_boost(tmp_path, monkeypatch):
    log = tmp_path / "log.txt"
    past = "1970-01-01T00:00:00"
    log.write_text(f"{past} Prediction: aaa... ent=0.00\n")
    model_file = tmp_path / "model.txt"
    model = {"n": 2, "model": {"a": {"b": 1}}}
    model_file.write_text(json.dumps(model))
    sixth_feeling._mini_le = SimpleNamespace(
        LOG_FILE=str(log),
        MODEL_FILE=str(model_file),
        load_model=lambda: json.loads(model_file.read_text()),
    )
    sixth_feeling.LOG_FILE = str(log)
    sixth_feeling.MODEL_FILE = str(model_file)
    sixth_feeling.check_prediction("aaa")
    boosted = json.loads(model_file.read_text())
    assert boosted["model"]["a"]["b"] == 2
    assert "boosted" in log.read_text()


def test_check_prediction_pain(tmp_path, monkeypatch):
    log = tmp_path / "log.txt"
    past = "1970-01-01T00:00:00"
    log.write_text(f"{past} Prediction: aaa... ent=0.00\n")
    model_file = tmp_path / "model.txt"
    model_file.write_text(json.dumps({"n": 2, "model": {"a": {"b": 1}}}))
    sixth_feeling._mini_le = SimpleNamespace(
        LOG_FILE=str(log),
        MODEL_FILE=str(model_file),
        load_model=lambda: json.loads(model_file.read_text()),
    )
    sixth_feeling.LOG_FILE = str(log)
    sixth_feeling.MODEL_FILE = str(model_file)
    calls = []
    monkeypatch.setattr(sixth_feeling, "trigger_pain", lambda out: calls.append(True))
    sixth_feeling.check_prediction("xyz")
    assert calls
    assert "pain triggered" in log.read_text()
