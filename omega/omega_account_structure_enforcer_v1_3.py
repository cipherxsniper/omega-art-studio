#!/usr/bin/env python3

import sqlite3
import json
import hashlib

DB = "omega_ledger.db"


def hash_state(state):
    return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()


def run():
    print("🏦 OMEGA ACCOUNT STRUCTURE ENFORCER v1")

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT id, user_id, balance FROM accounts")
    rows = cur.fetchall()

    accounts = {
        "THOMAS_LH": False,
        "OMEGA_CREDIT": False,
        "OMEGA_RESERVE": False,
        "OMEGA_TREASURY": False,
        "OMEGA_INVESTMENT": False
    }

    for r in rows:
        acc_id = str(r[1]).upper()

        if "THOMAS" in acc_id:
            accounts["THOMAS_LH"] = True
        if "CREDIT" in acc_id:
            accounts["OMEGA_CREDIT"] = True
        if "RESERVE" in acc_id:
            accounts["OMEGA_RESERVE"] = True
        if "TREASURY" in acc_id:
            accounts["OMEGA_TREASURY"] = True
        if "INVEST" in acc_id:
            accounts["OMEGA_INVESTMENT"] = True

    missing = [k for k, v in accounts.items() if not v]

    result = {
        "existing_accounts": len(rows),
        "account_flags": accounts,
        "missing_structures": missing,
        "system_state": "STRUCTURALLY_COMPLETE" if len(missing) == 0 else "STRUCTURAL_GAPS_DETECTED"
    }

    result["deterministic_hash"] = hash_state(result)

    print(json.dumps(result, indent=2))

    conn.close()


if __name__ == "__main__":
    run()
