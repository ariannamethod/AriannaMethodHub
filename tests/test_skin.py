from arianna_core import skin


def test_calculate_entropy_zero():
    assert skin.calculate_entropy("aaaa") == 0.0


def test_affinity_count():
    text = "love resonance"
    ratio = skin.affinity(text)
    assert ratio > 0


def test_evolve_skin_modifies_html(tmp_path, monkeypatch):
    html = tmp_path / "index.html"
    html.write_text("<html><head></head><body></body></html>", encoding="utf-8")
    log = tmp_path / "log.txt"
    monkeypatch.setattr(skin, "LOG_FILE", str(log))
    monkeypatch.setattr(skin, "load_model", lambda: {})
    monkeypatch.setattr(skin, "generate", lambda *a, **k: "resonance")
    color = skin.evolve_skin(str(html))
    content = html.read_text(encoding="utf-8")
    assert "background" in content
    assert log.exists()
    assert color.startswith("#")
