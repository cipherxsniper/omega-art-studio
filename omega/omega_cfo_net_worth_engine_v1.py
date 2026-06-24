#!/usr/bin/env python3

import sqlite3
import json
from collections import defaultdict
from datetime import datetime, UTC

DB_PATH = "omega_ledger.db"


def utc_now():
    return datetime.now(UTC).isoformat()


def connect():
    return sqlite3.connect(DB_PATH)


def load_events(cur):
    cur.execute("""
        SELECT payload_json
        FROM ledger_events
        ORDER BY id ASC
    """)
    rows = cur.fetchall()
    return [json.loads(r[0]) for r in rows if r and r[0]]


def compute_net_worth(events):
    balances = defaultdict(float)

    for e in events:
        ledger_effect = e.get("ledger_effect", {})
        if not isinstance(ledger_effect, dict):
            continue

        for account, delta in ledger_effect.items():
            try:
                balances[account] += float(delta)
            except Exception:
                continue

    return dict(balances)


def total_system_value(balances):
    return sum(balances.values())


def enforce_zero_sum(balances):
    total = total_system_value(balances)
    balances["_SYSTEM_DRIFT_CHECK"] = total
    return balances


def run_net_worth_engine():
    conn = connect()
    cur = conn.cursor()

    events = load_events(cur)
    balances = compute_net_worth(events)
    balances = enforce_zero_sum(balances)

    conn.close()

    return {
        "status": "CFO_NET_WORTH_ENGINE_ACTIVE",
        "timestamp": utc_now(),
        "balances": balances,
        "total_system_value": total_system_value(balances)
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_net_worth_engine(), indent=2))
