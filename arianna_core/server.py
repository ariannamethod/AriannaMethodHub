from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from . import mini_le


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/chat'):
            from urllib.parse import urlparse, parse_qs
            query = parse_qs(urlparse(self.path).query)
            msg = query.get('msg', [''])[0]
            try:
                reply = mini_le.chat_response(msg)
            except Exception as e:
                reply = f"error: {e}"
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(reply.encode('utf-8'))
            return
        if self.path in ('/', '/index.html'):
            try:
                mini_le.run()
            except Exception as e:
                print('mini_le failed:', e)
        super().do_GET()


if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    ThreadingHTTPServer(('', port), Handler).serve_forever()
