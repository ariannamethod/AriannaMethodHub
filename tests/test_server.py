import http.client
import threading
from http.server import HTTPServer
from functools import partial
from pathlib import Path
import subprocess
import sys
import time
import json
import os

from arianna_core import server

ROOT = Path(__file__).resolve().parents[1]


def make_server(monkeypatch, chat_func=lambda m: "reply:" + m):
    monkeypatch.setattr(server.mini_le, "chat_response", chat_func)
    handler = partial(server.Handler, directory=str(server.ROOT))
    srv = HTTPServer(("localhost", 0), handler)
    return srv


def get(srv, path):
    port = srv.server_address[1]
    conn = http.client.HTTPConnection("localhost", port)
    conn.request("GET", path)
    resp = conn.getresponse()
    body = resp.read().decode()
    headers = dict(resp.getheaders())
    conn.close()
    return resp.status, body, headers


def head(srv, path):
    port = srv.server_address[1]
    conn = http.client.HTTPConnection("localhost", port)
    conn.request("HEAD", path)
    resp = conn.getresponse()
    headers = dict(resp.getheaders())
    conn.close()
    return resp.status, headers


def test_chat_endpoint(monkeypatch):
    srv = make_server(monkeypatch)
    thread = threading.Thread(target=srv.handle_request)
    thread.start()
    status, body, headers = get(srv, "/chat?msg=hi")
    thread.join()
    srv.server_close()
    assert status == 200
    assert "reply:hi" in body
    assert headers.get("Access-Control-Allow-Origin") == "*"


def test_chat_post_endpoint(monkeypatch):
    srv = make_server(monkeypatch)
    thread = threading.Thread(target=srv.handle_request)
    thread.start()
    port = srv.server_address[1]
    conn = http.client.HTTPConnection("localhost", port)
    conn.request("POST", "/chat", body="hello", headers={"Content-Type": "text/plain"})
    resp = conn.getresponse()
    body = resp.read().decode()
    headers = dict(resp.getheaders())
    conn.close()
    thread.join()
    srv.server_close()
    assert resp.status == 200
    assert "reply:hello" in body
    assert headers.get("Access-Control-Allow-Origin") == "*"


def test_root_serves_index(monkeypatch):
    srv = make_server(monkeypatch)
    thread = threading.Thread(target=srv.handle_request)
    thread.start()
    status, body, _ = get(srv, "/")
    thread.join()
    srv.server_close()
    assert status == 200
    assert "<!DOCTYPE html>" in body


def test_server_runs_as_module():
    port = 8765
    proc = subprocess.Popen(
        [sys.executable, "-m", "arianna_core.server", str(port)],
        cwd=str(ROOT),
    )
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


def test_server_root_from_temp_dir(tmp_path):
    port = 8766
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    proc = subprocess.Popen(
        [sys.executable, "-m", "arianna_core.server", str(port)],
        cwd=str(tmp_path),
        env=env,
    )
    try:
        time.sleep(0.3)
        conn = http.client.HTTPConnection("localhost", port)
        conn.request("GET", "/")
        resp = conn.getresponse()
        body = resp.read().decode()
        conn.close()
        assert resp.status == 200
        assert "<!DOCTYPE html>" in body
    finally:
        proc.terminate()
        proc.wait()


def test_head_root(monkeypatch):
    srv = make_server(monkeypatch)
    thread = threading.Thread(target=srv.handle_request)
    thread.start()
    status, headers = head(srv, "/")
    thread.join()
    srv.server_close()
    assert status == 200
    assert "text/html" in headers.get("Content-type", "")


def test_missing_file(monkeypatch):
    srv = make_server(monkeypatch)
    thread = threading.Thread(target=srv.handle_request)
    thread.start()
    status, body, _ = get(srv, "/no_such_file.txt")
    thread.join()
    srv.server_close()
    assert status == 404


def test_health_endpoint(monkeypatch):
    srv = make_server(monkeypatch)
    thread = threading.Thread(target=srv.handle_request)
    thread.start()
    status, body, headers = get(srv, "/health")
    thread.join()
    srv.server_close()
    assert status == 200
    assert headers.get("Content-Type", "").startswith("application/json")
    data = json.loads(body)
    assert data["status"] == "alive"
