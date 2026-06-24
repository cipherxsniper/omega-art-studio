#!/usr/bin/env python3

import sqlite3
import json

DB_PATH = "omega_ledger.db"


def connect_db():
    return sqlite3.connect(DB_PATH)


def load_ledger_balances():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT payload_json
        FROM ledger_events
    """)

    balances = {}

    for (payload_str,) in cur.fetchall():
        if not payload_str:
            continue

        try:
            payload = json.loads(payload_str)
        except Exception:
            continue

        effects = payload.get("ledger_effect", {})

        for k, v in effects.items():
            try:
                balances[k] = balances.get(k, 0.0) + float(v)
            except Exception:
                continue

    conn.close()
    return balances


def project_identity_graph():
    balances = load_ledger_balances()

    return {
        "users": {},
        "wallets": {},
        "accounts": {},
        "events": [],
        "balances": balances
    }


def run():
    graph = project_identity_graph()

    print("🧠 LEDGER → IDENTITY PROJECTION ACTIVE")
    print(json.dumps(graph, indent=2))


if __name__ == "__main__":
    run()
