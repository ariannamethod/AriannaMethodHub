from http.server import SimpleHTTPRequestHandler, HTTPServer
import mini_le

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ('/', '/index.html'):
            try:
                mini_le.run()
            except Exception as e:
                print('mini_le failed:', e)
        super().do_GET()

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    HTTPServer(('', port), Handler).serve_forever()
