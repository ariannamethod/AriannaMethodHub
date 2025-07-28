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


CHAT_LOG: list[tuple[str, str]] = []


class Handler(SimpleHTTPRequestHandler):
    def _render_page(self):
        """Return the chat HTML page."""
        messages = []
        for user, bot in CHAT_LOG:
            messages.append(f"<div class='message'>&gt; {user}</div>")
            messages.append(f"<div class='message'>{bot}</div>")
        log_html = "\n".join(messages)
        html = f"""
<!DOCTYPE html>
<html lang='ru'>
<head>
    <meta charset='UTF-8'>
    <title>LÉ</title>
    <style>
        body {{
            background: #fff;
            color: #000;
            font-family: 'Courier New', Courier, monospace;
            margin: 0;
            display: flex;
            flex-direction: column;
            height: 100vh;
        }}
        #chat-log {{
            flex: 1;
            overflow-y: auto;
            padding: 10px;
            box-sizing: border-box;
        }}
        form {{ margin: 0; }}
        #chat-input {{
            width: 100%;
            box-sizing: border-box;
            padding: 10px;
            border-top: 1px solid #ccc;
        }}
        .message {{ margin: 5px 0; }}
    </style>
</head>
<body>
    <div id='chat-log'>{log_html}</div>
    <form action='/chat' method='get'>
        <input id='chat-input' name='msg' type='text' autofocus autocomplete='off'>
    </form>
</body>
</html>
        """
        return html.encode('utf-8')

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
            msg = query.get('msg', [''])[0].strip()
            if msg:
                try:
                    reply = mini_le.chat_response(msg)
                except Exception as e:
                    reply = f"error: {e}"
                CHAT_LOG.append((msg, reply))
                if is_enabled("entropy"):
                    background(entropy_resonance.run_once)
                if is_enabled("pain"):
                    background(pain.check_once)
                if is_enabled("sixth_sense"):
                    background(sixth_feeling.predict_next)
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(self._render_page())
            return
        if self.path in ('/', '/index.html'):
            try:
                mini_le.run()
            except Exception as e:
                logging.error(f"mini_le failed: {e}")
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(self._render_page())
            return
        super().do_GET()


if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    ThreadingHTTPServer(('', port), Handler).serve_forever()
