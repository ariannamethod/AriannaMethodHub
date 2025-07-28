import time
import threading
from arianna_core import config, entropy_resonance, pain, sixth_feeling
from tests.test_server import make_server, get


def test_all_modules_with_disabled_features(monkeypatch):
    backup = config.FEATURES.copy()
    for k in config.FEATURES:
        config.FEATURES[k] = False
    try:
        # calls should simply skip
        entropy_resonance.run_once()
        pain.check_once()
        sixth_feeling.predict_next({})
    finally:
        config.FEATURES.update(backup)


def test_background_execution(monkeypatch):
    # enable features
    for k in config.FEATURES:
        config.FEATURES[k] = True
    monkeypatch.setattr(entropy_resonance, "run_once", lambda: time.sleep(0.3))
    monkeypatch.setattr(pain, "check_once", lambda: time.sleep(0.3))
    monkeypatch.setattr(sixth_feeling, "predict_next", lambda: time.sleep(0.3))

    srv = make_server(monkeypatch)
    thread = threading.Thread(target=srv.handle_request)
    thread.start()
    start = time.perf_counter()
    status, _ = get(srv, "/chat?msg=hi")
    duration = time.perf_counter() - start
    thread.join()
    srv.server_close()

    assert status == 200
    assert duration < 0.2
