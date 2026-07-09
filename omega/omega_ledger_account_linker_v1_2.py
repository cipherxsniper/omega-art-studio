#!/usr/bin/env python3

import sqlite3
import json

DB = "omega_ledger.db"


def extract_account_id(payload):
    try:
        if isinstance(payload, str):
            payload = json.loads(payload)
        return payload.get("account_id")
    except:
        return None


def run():
    print("🧾 OMEGA LEDGER ACCOUNT LINKER v1")

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT id, payload, type, timestamp FROM ledger_events")
    rows = cur.fetchall()

    linked = 0
    missing = 0

    for r in rows:
        event_id, payload, event_type, ts = r

        acc = extract_account_id(payload)

        if acc:
            linked += 1
        else:
            missing += 1

    result = {
        "total_events": len(rows),
        "linked_events": linked,
        "unlinked_events": missing,
        "binding_ratio": linked / len(rows) if rows else 0.0
    }

    print(json.dumps(result, indent=2))

    conn.close()


if __name__ == "__main__":
    run()
