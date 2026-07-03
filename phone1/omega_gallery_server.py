#!/usr/bin/env python3
import http.server, os, re, urllib.request

HOME = "/data/data/com.termux/files/home"
os.chdir(HOME)

def get_api_url():
    try:
        r = urllib.request.urlopen("http://127.0.0.1:8085/current-api", timeout=2)
        import json
        d = json.loads(r.read())
        return d.get("api", "")
    except:
        return ""

class OmegaHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ["/omega_gallery.html", "/", ""]:
            try:
                with open(HOME + "/omega_gallery.html", "r") as f:
                    content = f.read()
                api_url = get_api_url()
                if api_url:
                    content = re.sub(
                        r"var API_URL = '[^']*';",
                        f"var API_URL = '{api_url}';",
                        content
                    )
                encoded = content.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", len(encoded))
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
                self.end_headers()
                self.wfile.write(encoded)
                return
            except Exception as e:
                pass
        super().do_GET()

    def log_message(self, format, *args):
        pass

http.server.test(OmegaHandler, port=8090, bind="127.0.0.1")
