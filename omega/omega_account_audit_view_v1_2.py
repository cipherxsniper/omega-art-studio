#!/usr/bin/env python3

import json
import sqlite3

DB_PATH = "omega_ledger.db"


def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return {}


def get_wallets():
    return load_json("omega_wallets.json")


def get_settlement():
    return load_json("omega_settlement.json")


def get_db_accounts():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT event_type, payload_json, created_at FROM ledger_events ORDER BY id DESC LIMIT 200")
    rows = cur.fetchall()
    conn.close()

    return rows


def build_view():
    wallets = get_wallets()
    settlement = get_settlement()
    events = get_db_accounts()

    balances = {}

    # wallet layer
    for _, w in wallets.items():
        wid = w.get("wallet_id")
        balances[wid] = w.get("balance", 0.0)

    # settlement layer
    for k, v in settlement.get("accounts", {}).items() if isinstance(settlement.get("accounts"), dict) else []:
        balances[k] = v

    # ledger scan (truth reconstruction)
    for e in events:
        try:
            payload = json.loads(e[1]) if e[1] else {}
            effects = payload.get("ledger_effect", {})
            for acc, amt in effects.items():
                balances[acc] = balances.get(acc, 0.0) + float(amt)
        except:
            pass

    return {
        "wallets": wallets,
        "settlement": settlement,
        "reconstructed_balances": balances,
        "ledger_event_count": len(events)
    }


if __name__ == "__main__":
    print(json.dumps(build_view(), indent=2))
