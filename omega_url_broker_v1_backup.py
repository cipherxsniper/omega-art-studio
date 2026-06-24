#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

CURRENT_TUNNEL = "https://pursue-carriers-humanities-shipped.trycloudflare.com"

class BrokerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/current-api":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"api": CURRENT_TUNNEL}).encode())
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "online"}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8085), BrokerHandler)
    print(f"URL Broker listening on 8085 → {CURRENT_TUNNEL}")
    server.serve_forever()
