from pathlib import Path
from functools import partial
import http.client
import threading
from http.server import HTTPServer
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arianna_core import server  # noqa: E402


def make_server(monkeypatch, run_func=lambda: None, chat_func=lambda m: "reply:" + m):
    monkeypatch.setattr(server.mini_le, "run", run_func)
    monkeypatch.setattr(server.mini_le, "chat_response", chat_func)
    handler = partial(server.Handler, directory=str(ROOT))
    srv = HTTPServer(("localhost", 0), handler)
    return srv


def get(srv, path):
    port = srv.server_address[1]
    conn = http.client.HTTPConnection("localhost", port)
    conn.request("GET", path)
    resp = conn.getresponse()
    body = resp.read().decode()
    conn.close()
    return resp.status, body


def test_chat_endpoint(monkeypatch):
    srv = make_server(monkeypatch)
    thread = threading.Thread(target=srv.handle_request)
    thread.start()
    status, body = get(srv, "/chat?msg=hi")
    thread.join()
    srv.server_close()
    assert status == 200
    assert body == "reply:hi"


def test_root_triggers_run(monkeypatch):
    called = []

    def fake_run():
        called.append(True)

    srv = make_server(monkeypatch, run_func=fake_run)
    thread = threading.Thread(target=srv.handle_request)
    thread.start()
    status, body = get(srv, "/")
    thread.join()
    srv.server_close()
    assert called
    assert status == 200
    assert "<!DOCTYPE html>" in body
