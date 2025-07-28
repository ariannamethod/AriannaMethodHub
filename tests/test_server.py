import http.client
import threading
from http.server import HTTPServer
from functools import partial
from pathlib import Path

from arianna_core import server

ROOT = Path(__file__).resolve().parents[1]


def make_server(monkeypatch, chat_func=lambda m: "reply:" + m):
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
    assert "reply:hi" in body


def test_root_serves_index(monkeypatch):
    srv = make_server(monkeypatch)
    thread = threading.Thread(target=srv.handle_request)
    thread.start()
    status, body = get(srv, "/")
    thread.join()
    srv.server_close()
    assert status == 200
    assert "<!DOCTYPE html>" in body
