from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import os
import sys

if __package__ is None:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    import mini_le
else:
    from . import mini_le

ROOT = os.path.join(os.path.dirname(__file__), "..")


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
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
    HTTPServer(("", port), Handler).serve_forever()


if __name__ == "__main__":
    import sys

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    serve(port)
