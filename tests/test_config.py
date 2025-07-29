import importlib
from arianna_core import config


def test_settings_env_override(monkeypatch):
    monkeypatch.setenv("ARIANNA_NGRAM_LEVEL", "3")
    importlib.reload(config)
    assert config.settings.n_gram_level == 3
    monkeypatch.delenv("ARIANNA_NGRAM_LEVEL")
    importlib.reload(config)


def test_is_enabled_default():
    assert config.is_enabled("entropy") is True
    assert config.is_enabled("skin") is False
