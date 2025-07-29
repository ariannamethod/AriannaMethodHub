import http.client
import threading
from http.server import HTTPServer
from functools import partial
from pathlib import Path
import subprocess
import sys
import time

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


def test_server_runs_as_script(tmp_path):
    port = 8765
    proc = subprocess.Popen([
        sys.executable,
        "arianna_core/server.py",
        str(port),
    ], cwd=str(ROOT))
    try:
        time.sleep(0.3)
        conn = http.client.HTTPConnection("localhost", port)
        conn.request("GET", "/chat?msg=hi")
        resp = conn.getresponse()
        body = resp.read().decode()
        conn.close()
        assert resp.status == 200
        assert body
    finally:
        proc.terminate()
        proc.wait()
