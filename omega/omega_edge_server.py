from http.server import BaseHTTPRequestHandler, HTTPServer
import json

PORT = 8080

class OmegaHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())

    def do_POST(self):
        if self.path == "/event":
            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)
            event = json.loads(body.decode())

            print("EVENT RECEIVED:", event)

            response = {
                "status": "RECEIVED",
                "decision": "APPROVED",
                "event_type": event.get("type", "UNKNOWN")
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

HTTPServer(("0.0.0.0", PORT), OmegaHandler).serve_forever()
