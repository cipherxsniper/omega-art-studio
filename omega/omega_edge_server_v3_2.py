from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import psycopg2
import uuid
import traceback

PORT = 8080

DB = psycopg2.connect(
    dbname="omega_bank",
    user="omega",
    host="localhost"
)

class OmegaHandler(BaseHTTPRequestHandler):

    def respond(self, code, payload):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def do_GET(self):
        if self.path == "/health":
            self.respond(200, {
                "status": "ok",
                "runtime": "OMEGA_V3"
            })

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
                gen_random_uuid(),
                %s,
                %s,
                'wallet',
                %s,
                NOW(),
                %s
            )
        """, (
            event["type"],
            event["wallet_id"],
            json.dumps(event),
            event_id
        ))

        DB.commit()

    def do_POST(self):

        try:

            if self.path != "/event":
                self.respond(404, {"error": "NOT_FOUND"})
                return

            content_length = int(self.headers["Content-Length"])

            body = self.rfile.read(content_length)

            event = json.loads(body.decode())

            print("\nEVENT RECEIVED")
            print(json.dumps(event, indent=2))

            self.write_event(event)

            self.respond(200, {
                "status": "RECEIVED",
                "decision": "APPROVED",
                "event_type": event.get("type")
            })

        except Exception as e:

            traceback.print_exc()

            self.respond(500, {
                "status": "ERROR",
                "message": str(e)
            })

print(f"OMEGA EDGE SERVER V3 RUNNING ON :{PORT}")

HTTPServer(("0.0.0.0", PORT), OmegaHandler).serve_forever()
