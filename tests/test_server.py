# ruff: noqa: E402
from pathlib import Path
from functools import partial
import http.client
import threading
from http.server import HTTPServer

ROOT = Path(__file__).resolve().parents[1]

from arianna_core import server  # noqa: E402


def make_server(
    monkeypatch,
    run_func=lambda: None,
    chat_func=lambda m: "reply:" + m,
):
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


def test_chat_sanitizes_input(monkeypatch, tmp_path):
    log = tmp_path / "log.txt"
    received = {}

    def fake_chat(msg):
        received["msg"] = msg
        with open(log, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
        return "reply"

    srv = make_server(monkeypatch, chat_func=fake_chat)
    thread = threading.Thread(target=srv.handle_request)
    thread.start()
    status, body = get(srv, "/chat?msg=bad%0A<script>")
    thread.join()
    srv.server_close()

    assert status == 200
    assert body == "reply"
    # message passed to chat should be sanitized
    assert "\n" not in received["msg"] and "\r" not in received["msg"]
    assert "<" not in received["msg"]
    content = log.read_text(encoding="utf-8").splitlines()
    # log file should contain exactly one line with sanitized message
    assert len(content) == 1
    assert content[0] == received["msg"]


def test_chat_handles_missing_msg(monkeypatch, tmp_path):
    log = tmp_path / "log.txt"

    def fake_chat(msg):
        with open(log, "a", encoding="utf-8") as f:
            f.write((msg or "<empty>") + "\n")
        return "ok"

    srv = make_server(monkeypatch, chat_func=fake_chat)
    thread = threading.Thread(target=srv.handle_request)
    thread.start()
    status, body = get(srv, "/chat")
    thread.join()
    srv.server_close()

    assert status == 200
    assert body == "ok"
    # log should have single sanitized line even with missing msg
    content = log.read_text(encoding="utf-8").splitlines()
    assert len(content) == 1
    assert content[0] == "<empty>"
