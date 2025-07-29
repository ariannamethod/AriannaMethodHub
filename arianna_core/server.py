from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from functools import partial
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
    def end_headers(self) -> None:
        # Allow cross-origin requests so the HTML page can talk to the server
        # even when served from a different port or domain.
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def do_GET(self) -> None:
        if self.path.startswith("/chat"):
            query = parse_qs(urlparse(self.path).query)
            msg = query.get("msg", [""])[0]
            reply = mini_le.chat_response(msg)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(reply.encode("utf-8"))
        else:
            if self.path == "/":
                self.path = "/index.html"
            super().do_GET()


def serve(port: int = 8000) -> None:
    handler = partial(Handler, directory=str(ROOT))
    HTTPServer(("", port), handler).serve_forever()


if __name__ == "__main__":
    import sys

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    serve(port)
