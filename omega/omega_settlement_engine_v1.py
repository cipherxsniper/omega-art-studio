import sqlite3
import ast
from datetime import datetime

DB = "omega_ledger.db"

def load_events(cur):
    cur.execute("SELECT id, type, payload, timestamp FROM ledger_events")
    return cur.fetchall()

def apply_settlement(events):
    balances = {
        "OMEGA_TREASURY": 0.0,
        "OMEGA_CREDIT": 0.0,
        "OMEGA_RESERVE": 0.0,
        "OMEGA_INVESTMENT": 0.0,
        "THOMAS_LH": 0.0
    }

    for _id, _type, payload, ts in events:
        try:
            effect = ast.literal_eval(payload)
            for k, v in effect.items():
                if k in balances:
                    balances[k] += float(v)
        except:
            continue

    return balances

def run():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    events = load_events(cur)
    balances = apply_settlement(events)

    snapshot = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_count": len(events),
        "settled_balances": balances,
        "system_state": "SETTLEMENT_COMPLETE"
    }

    print("🏦 OMEGA SETTLEMENT ENGINE v1")
    print(snapshot)

    conn.close()

if __name__ == "__main__":
    run()
