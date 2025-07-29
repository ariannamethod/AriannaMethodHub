from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from functools import partial
import json
import os
import sys

from typing import TYPE_CHECKING

if __package__ is None:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    import importlib
    mini_le = importlib.import_module("arianna_core.mini_le")  # type: ignore
else:
    from . import mini_le

if TYPE_CHECKING:
    from . import mini_le as _mini_le_mod  # noqa: F401

ROOT = os.path.join(os.path.dirname(__file__), "..")


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
            self.send_response(200)
            self._set_cors_headers()
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(reply.encode("utf-8"))
        elif self.path == "/health":
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


if __name__ == "__main__":
    import sys

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    serve(port)
