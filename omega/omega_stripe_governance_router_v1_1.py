#!/usr/bin/env python3

import json
import hashlib
import sqlite3
from datetime import datetime

DB = "omega_ledger.db"


def hash_state(state):
    return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()


def route_account(layer):
    if layer == "REVENUE_LAYER":
        return "CREDIT_AND_RESERVE_SPLIT"
    if layer == "SYSTEM_LAYER":
        return "SYSTEM_ROUTED"
    if layer == "PERSONAL_LAYER":
        return "OWNER_ALLOCATION"
    return "UNROUTED"


def run():
    print("💳 OMEGA STRIPE GOVERNANCE ROUTER v1")

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, user_id, balance
        FROM accounts
    """)

    rows = cur.fetchall()

    events = []

    for r in rows:
        acc_id, name, balance = r

        if "REVENUE" in name.upper():
            layer = "REVENUE_LAYER"
        elif "SYSTEM" in name.upper():
            layer = "SYSTEM_LAYER"
        elif "TOMMY" in name.upper():
            layer = "PERSONAL_LAYER"
        else:
            layer = "UNROUTED"

        routing = route_account(layer)

        events.append({
            "account_id": acc_id,
            "name": name,
            "layer": layer,
            "routing_decision": routing,
            "timestamp": datetime.utcnow().isoformat()
        })

    result = {
        "event_count": len(events),
        "routing_table": events,
        "system_state": "STRIPE_ROUTING_READY"
    }

    result["deterministic_hash"] = hash_state(result)

    print(json.dumps(result, indent=2))

    conn.close()


if __name__ == "__main__":
    run()
