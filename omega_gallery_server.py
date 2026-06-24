#!/usr/bin/env python3
"""Custom gallery server — injects live API tunnel URL into HTML before serving."""
import json
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.request import urlopen

HOME = Path.home()

def get_current_api_url():
    try:
        with urlopen("http://127.0.0.1:8085/current-all", timeout=2) as r:
            data = json.load(r)
            return data.get("api", "http://127.0.0.1:8082")
    except Exception:
        return "http://127.0.0.1:8082"

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(HOME), **kwargs)

    def do_GET(self):
        if self.path == "/omega_gallery_v2.html" or self.path == "/":
            api_url = get_current_api_url()
            html = (HOME / "omega_gallery_v2.html").read_text()
            html = html.replace("__INJECT_API_URL__", api_url)
            body = html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

if __name__ == "__main__":
    port = 8090
    print(f"Gallery server with live injection on port {port}")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
