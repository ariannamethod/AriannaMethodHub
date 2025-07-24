from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path
from .core import generate_comment

ROOT = Path(__file__).resolve().parent.parent

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ('/', '/index.html'):
            comment = generate_comment()
            template = (ROOT / 'index.html').read_text(encoding='utf-8')
            html = template.replace('{{comment}}', comment)
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        else:
            super().do_GET()


def run(port: int = 8000):
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f'Serving on http://localhost:{port}')
    server.serve_forever()


if __name__ == '__main__':
    run()
