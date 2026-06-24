import sqlite3
import json

DB = "omega_ledger.db"

def get_events(cur):
    cur.execute("SELECT id, type, payload, timestamp FROM events ORDER BY rowid ASC")
    return cur.fetchall()

def normalize_event(event):
    event_id, event_type, payload, timestamp = event

    if isinstance(payload, dict):
        payload = json.dumps(payload, sort_keys=True)

    return {
        "id": event_id,
        "type": event_type,
        "payload": payload,
        "timestamp": timestamp
    }

def run():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    events = get_events(cur)
    normalized = [normalize_event(e) for e in events]

    print(f"RECONCILIATION_EVENTS={len(normalized)}")
    for e in normalized[:10]:
        print(e)

    conn.close()

if __name__ == "__main__":
    run()
