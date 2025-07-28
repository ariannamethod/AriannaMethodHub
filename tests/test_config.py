import importlib
import os

def test_safe_mode_env_disables_features(monkeypatch):
    monkeypatch.setenv("ARIANNA_SAFE_MODE", "1")
    import arianna_core.config as config
    importlib.reload(config)
    assert all(not v for v in config.FEATURES.values())
    monkeypatch.delenv("ARIANNA_SAFE_MODE", raising=False)
    importlib.reload(config)

