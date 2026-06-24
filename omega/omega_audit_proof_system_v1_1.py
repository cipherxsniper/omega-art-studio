import sqlite3
import hashlib
import json
from datetime import datetime

DB = "omega_ledger.db"

def sha256(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()

def get_last_chain_hash(cur):
    cur.execute("SELECT chain_hash FROM audit_log ORDER BY created_at DESC LIMIT 1")
    row = cur.fetchone()
    return row[0] if row else "GENESIS"

def build_event_fingerprint(event):
    return sha256(json.dumps(event, sort_keys=True))

def insert_audit(cur, event):
    event_id, event_type, payload, timestamp = event

    prev_hash = get_last_chain_hash(cur)

    event_dict = {
        "id": event_id,
        "type": event_type,
        "payload": payload,
        "timestamp": timestamp
    }

    event_hash = build_event_fingerprint(event_dict)

    chain_input = f"{prev_hash}{event_hash}"
    chain_hash = sha256(chain_input)

    audit_id = sha256(event_id + chain_hash)

    cur.execute("""
        INSERT INTO audit_log (
            id, event_id, event_hash, prev_hash, chain_hash
        ) VALUES (?, ?, ?, ?, ?)
    """, (audit_id, event_id, event_hash, prev_hash, chain_hash))

    return {
        "event_id": event_id,
        "event_hash": event_hash,
        "prev_hash": prev_hash,
        "chain_hash": chain_hash
    }

def run():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT id, type, payload, timestamp FROM events ORDER BY rowid ASC")
    events = cur.fetchall()

    results = []
    for e in events:
        results.append(insert_audit(cur, e))

    conn.commit()
    conn.close()

    print("🧾 AUDIT PROOF COMPLETE")
    print(json.dumps(results[-3:], indent=2))

if __name__ == "__main__":
    run()
