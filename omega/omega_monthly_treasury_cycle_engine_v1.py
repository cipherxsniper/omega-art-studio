import time
import uuid
from datetime import datetime
import sqlite3

DB = "omega_ledger.db"

ACCOUNTS = [
    "OMEGA_TREASURY",
    "OMEGA_CREDIT",
    "OMEGA_RESERVE",
    "OMEGA_INVESTMENT",
    "THOMAS_LH"
]

def create_cycle_event():
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": "MONTHLY_TREASURY_CYCLE",
        "timestamp": datetime.now().isoformat(),
        "ledger_effect": {
            "OMEGA_TREASURY": +1950000000.0,
            "OMEGA_CREDIT": -500000000.0,
            "OMEGA_INVESTMENT": -1500000000.0,
            "THOMAS_LH": -50000000.0
        },
        "currency": "USD"
    }

def write_event(cur, event):
    cur.execute("""
        INSERT INTO ledger_events (id, type, payload, timestamp)
        VALUES (?, ?, ?, ?)
    """, (
        event["event_id"],
        event["event_type"],
        str(event["ledger_effect"]),
        event["timestamp"]
    ))

def run_cycle():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    event = create_cycle_event()
    write_event(cur, event)

    conn.commit()
    conn.close()

    print("🔁 MONTHLY TREASURY CYCLE COMPLETE")
    print(event)

if __name__ == "__main__":
    run_cycle()
