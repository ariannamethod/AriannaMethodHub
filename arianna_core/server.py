from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import mini_le


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/chat'):
            query = parse_qs(urlparse(self.path).query)
            msg = query.get('msg', [''])[0]
            reply = mini_le.chat_response(msg)
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(reply.encode('utf-8'))
        else:
            if self.path == '/':
                self.path = '/index.html'
            super().do_GET()


if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    ThreadingHTTPServer(('', port), Handler).serve_forever()
