#!/usr/bin/env python3

import sqlite3
import json
import hashlib

DB = "omega_ledger.db"


def hash_state(state):
    return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()


def classify_account(name: str):
    n = name.upper()

    if "THOMAS" in n:
        return "PERSONAL_CORE"
    if "CREDIT" in n:
        return "CREDIT_LAYER"
    if "RESERVE" in n:
        return "RESERVE_LAYER"
    if "MERCHANT" in n:
        return "MERCHANT_LAYER"
    if "TREASURY" in n:
        return "TREASURY_LAYER"
    if "INVEST" in n:
        return "INVESTMENT_LAYER"

    return "UNCLASSIFIED"


def run():
    print("🏦 OMEGA ACCOUNT STRUCTURE ENFORCER v2 (REAL MAPPING)")

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT id, user_id, balance FROM accounts")
    rows = cur.fetchall()

    mapped = []
    layers = {}

    for r in rows:
        acc_id, user_id, balance = r

        layer = classify_account(user_id)

        mapped.append({
            "account_id": acc_id,
            "name": user_id,
            "balance": balance,
            "layer": layer
        })

        layers[layer] = layers.get(layer, 0) + 1

    result = {
        "total_accounts": len(rows),
        "layer_distribution": layers,
        "mapped_accounts": mapped,
        "system_state": "CANONICAL_MAPPING_COMPLETE"
    }

    result["deterministic_hash"] = hash_state(result)

    print(json.dumps(result, indent=2))

    conn.close()


if __name__ == "__main__":
    run()
