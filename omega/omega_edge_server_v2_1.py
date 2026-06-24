from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import psycopg2
import uuid
from datetime import datetime

PORT = 8080

DB = psycopg2.connect(
    dbname="omega_bank",
    user="omega",
    host="localhost"
)

DB.autocommit = True

class OmegaHandler(BaseHTTPRequestHandler):

    def write_event(self, event):

        cur = DB.cursor()

        event_id = str(uuid.uuid4())

        cur.execute("""
            INSERT INTO ledger_events (
                id,
                event_type,
                aggregate_id,
                aggregate_type,
                payload,
                created_at,
                idempotency_key
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                NOW(),
                %s
            )
        """, (
            event_id,
            event.get("type"),
            event.get("wallet_id"),
            "WALLET",
            json.dumps(event),
            event.get("event_id")
        ))

        cur.close()

    def do_GET(self):

        if self.path == "/health":

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            self.wfile.write(json.dumps({
                "status": "ok",
                "runtime": "OMEGA_V2"
            }).encode())

    def do_POST(self):

        if self.path == "/event":

            content_length = int(self.headers["Content-Length"])

            body = self.rfile.read(content_length)

            event = json.loads(body.decode())

            print("\nEVENT RECEIVED")
            print(json.dumps(event, indent=2))

            self.write_event(event)

            response = {
                "status": "RECEIVED",
                "decision": "APPROVED",
                "event_type": event.get("type"),
                "timestamp": str(datetime.utcnow())
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            self.wfile.write(json.dumps(response).encode())

HTTPServer(("0.0.0.0", PORT), OmegaHandler).serve_forever()
