import json
import time
import hashlib

def create_snapshot(conn):
    cur = conn.cursor()

    cur.execute("SELECT * FROM ledger_events")
    events = cur.fetchall()

    snapshot = {
        "timestamp": time.time(),
        "events": events
    }

    raw = json.dumps(snapshot, default=str).encode()
    h = hashlib.sha256(raw).hexdigest()

    filename = f"omega_snapshot_{int(time.time())}.json"

    with open(filename, "w") as f:
        json.dump(snapshot, f, indent=2)

    return {
        "file": filename,
        "hash": h
    }
