from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from functools import partial
import json
import os
import queue
import sqlite3
import sys
import threading
import time

from typing import TYPE_CHECKING

from . import mini_le

if TYPE_CHECKING:
    from . import mini_le as _mini_le_mod  # noqa: F401

ROOT = os.path.join(os.path.dirname(__file__), "..")
EVENT_DB = os.path.join(os.path.dirname(__file__), "events.db")


class AppState:
    """Background worker that persists events asynchronously."""

    def __init__(self, db_path: str = EVENT_DB, ttl_events: float = -1.0) -> None:
        self.db_path = db_path
        self.ttl_events = ttl_events
        self.queue: "queue.Queue[tuple[str, int, str]]" = queue.Queue()
        self._index = 0
        self.worker = threading.Thread(target=self.worker_loop, daemon=True)
        self.worker.start()

    def worker_loop(self) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                event_type TEXT,
                idx INTEGER,
                ip TEXT,
                ts REAL
            )
            """
        )
        while True:
            event_type, index, ip = self.queue.get()
            now = time.time()
            with conn:
                conn.execute(
                    "INSERT INTO events(event_type, idx, ip, ts) VALUES (?,?,?,?)",
                    (event_type, index, ip, now),
                )
                if self.ttl_events >= 0:
                    cutoff = now - self.ttl_events
                    conn.execute("DELETE FROM events WHERE ts < ?", (cutoff,))
            self.queue.task_done()

    def enqueue_event(self, event_type: str, ip: str) -> None:
        self._index += 1
        self.queue.put((event_type, self._index, ip))


app_state = AppState()


class Handler(SimpleHTTPRequestHandler):
    """Serve static files and a simple chat endpoint with CORS."""

    def _set_cors_headers(self) -> None:
        """Send standard CORS headers."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self) -> None:  # pragma: no cover - simple headers only
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        """Handle GET requests for chat, health and static files."""
        if self.path.startswith("/chat"):
            query = parse_qs(urlparse(self.path).query)
            msg = query.get("msg", [""])[0]
            reply = mini_le.chat_response(msg)
            app_state.enqueue_event("chat", self.client_address[0])
            self.send_response(200)
            self._set_cors_headers()
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(reply.encode("utf-8"))
        elif self.path == "/health":
            app_state.enqueue_event("health", self.client_address[0])
            self.send_response(200)
            self._set_cors_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            data = {
                "status": "alive",
                "entropy": getattr(mini_le, "last_entropy", 0.0),
            }
            self.wfile.write(json.dumps(data).encode("utf-8"))
        else:
            if self.path == "/":
                self.path = "/index.html"
            super().do_GET()

    def do_POST(self) -> None:
        """Handle chat POST requests."""
        if self.path.startswith("/chat"):
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8") if length > 0 else ""
            reply = mini_le.chat_response(body)
            app_state.enqueue_event("chat", self.client_address[0])
            self.send_response(200)
            self._set_cors_headers()
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(reply.encode("utf-8"))
        else:
            self.send_response(404)
            self._set_cors_headers()
            self.end_headers()


def serve(port: int = 8000) -> None:
    handler = partial(Handler, directory=str(ROOT))
    HTTPServer(("", port), handler).serve_forever()


if __name__ == "__main__":  # pragma: no cover
    if __package__ is None or __package__ == "":
        raise SystemExit("Run this module with `python -m arianna_core.server`.")
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    serve(port)
