#!/usr/bin/env python3

import sqlite3
import json
import hashlib

DB = "omega_ledger.db"


def hash_state(state):
    return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()


def semantic_map(name: str):
    n = name.upper()

    # REALISTIC FINTECH SEMANTIC MAPPING
    if "SYSTEM" in n:
        return "SYSTEM_LAYER"

    if "REVENUE" in n:
        return "REVENUE_LAYER"

    if "THOMAS" in n or "TOMMY" in n:
        return "PERSONAL_LAYER"

    if "CREDIT" in n:
        return "CREDIT_LAYER"

    if "RESERVE" in n:
        return "RESERVE_LAYER"

    if "TREASURY" in n:
        return "TREASURY_LAYER"

    if "INVEST" in n:
        return "INVESTMENT_LAYER"

    return "UNCLASSIFIED_LAYER"


def run():
    print("🧠 OMEGA SEMANTIC ACCOUNT ONTOLOGY MAPPER v1")

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT id, user_id, balance FROM accounts")
    rows = cur.fetchall()

    mapped = []
    distribution = {}

    for r in rows:
        acc_id, user_id, balance = r

        layer = semantic_map(user_id)

        mapped.append({
            "account_id": acc_id,
            "name": user_id,
            "balance": balance,
            "semantic_layer": layer
        })

        distribution[layer] = distribution.get(layer, 0) + 1

    result = {
        "total_accounts": len(rows),
        "semantic_distribution": distribution,
        "mapped_accounts": mapped,
        "system_state": "SEMANTIC_ONTOLOGY_READY"
    }

    result["deterministic_hash"] = hash_state(result)

    print(json.dumps(result, indent=2))

    conn.close()


if __name__ == "__main__":
    run()
