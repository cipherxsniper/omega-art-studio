#!/usr/bin/env python3

import sqlite3
import json
from collections import defaultdict

DB_PATH = "omega_ledger.db"


def extract_event(payload):
    """
    Safe decoder for event payload.
    Supports:
    - JSON string payload
    - dict-like payload already parsed
    """
    try:
        if isinstance(payload, str):
            data = json.loads(payload)
        else:
            data = payload
    except Exception:
        return None

    return {
        "account_id": data.get("account_id"),
        "amount": float(data.get("amount", 0)),
        "type": data.get("type")
    }


def compute_balances(cur):
    balances = defaultdict(float)

    cur.execute("SELECT payload FROM ledger_events")
    rows = cur.fetchall()

    for (payload,) in rows:
        event = extract_event(payload)
        if not event:
            continue

        account_id = event["account_id"]
        amount = event["amount"]

        if account_id:
            balances[account_id] += amount

    return balances


def sync_accounts(cur, balances):
    for account_id, balance in balances.items():
        cur.execute("""
            UPDATE accounts
            SET balance = ?
            WHERE id = ?
        """, (balance, account_id))


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    balances = compute_balances(cur)
    sync_accounts(cur, balances)

    conn.commit()

    print("📊 BALANCE PROJECTION COMPLETE (SAFE)")
    for k, v in balances.items():
        print(k, v)

    conn.close()


if __name__ == "__main__":
    run()
