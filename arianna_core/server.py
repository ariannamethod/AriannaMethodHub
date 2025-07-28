from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import threading
import asyncio
import logging
import json
from . import mini_le, entropy_resonance, pain, sixth_feeling
from .config import is_enabled, FEATURES


def background(fn, *args, **kwargs):
    """Run ``fn`` in a daemon thread without blocking the response."""

    def wrapper():
        try:
            if asyncio.iscoroutinefunction(fn):
                asyncio.run(fn(*args, **kwargs))
            else:
                fn(*args, **kwargs)
        except Exception as e:  # pragma: no cover - log failures
            logging.error(f"Background task failed: {e}")

    threading.Thread(target=wrapper, daemon=True).start()


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            try:
                health_data = {
                    "entropy": getattr(mini_le, 'last_entropy', 0),
                    "novelty": getattr(mini_le, 'RECENT_NOVELTY', 0),
                    "pain_events": getattr(pain, 'event_count', 0) if is_enabled('pain') else 'disabled',
                    "features": FEATURES,
                    "status": "healthy",
                }
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(health_data, indent=2).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
            return
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
            if is_enabled("entropy"):
                background(entropy_resonance.run_once)
            if is_enabled("pain"):
                background(pain.check_once)
            if is_enabled("sixth_sense"):
                background(sixth_feeling.predict_next)
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
