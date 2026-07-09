import uuid
from datetime import datetime
import sqlite3

DB = "omega_ledger.db"

def create_event():
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": "MANUAL_CAPITAL_DISTRIBUTION",
        "timestamp": datetime.now().isoformat(),
        "ledger_effect": {
            "OMEGA_TREASURY": -1950000000.0,
            "OMEGA_CREDIT": 500000000.0,
            "OMEGA_INVESTMENT": 1500000000.0,
            "THOMAS_LH": 50000000.0
        },
        "currency": "USD"
    }

def insert_event(cur, event):
    cur.execute("""
        INSERT INTO ledger_events (id, type, payload, timestamp)
        VALUES (?, ?, ?, ?)
    """, (
        event["event_id"],
        event["event_type"],
        str(event["ledger_effect"]),
        event["timestamp"]
    ))

def run():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    event = create_event()
    insert_event(cur, event)

    conn.commit()
    conn.close()

    print("💰 CAPITAL DISTRIBUTION EVENT APPLIED")
    print(event)

if __name__ == "__main__":
    run()
