#!/usr/bin/env python3

import os
import sqlite3
import json
from pathlib import Path

ROOT = Path.home() / "Omega-Production" / "omega_bank"

DBS = [
    "omega_ledger.db",
    "omega_bank.db",
    "billing.db",
    "event_queue.db",
    "omega_users.db",
]

REQUIRED_TABLES = {
    "omega_ledger.db": [
        "ledger_events",
        "accounts",
        "finalized_events",
        "subscriptions",
    ]
}

results = {
    "databases": {},
    "tables": {},
    "counts": {},
    "summary": {}
}

pass_count = 0
fail_count = 0

for db in DBS:
    db_path = ROOT / db
    exists = db_path.exists()
    results["databases"][db] = exists

    if exists:
        pass_count += 1
    else:
        fail_count += 1

for db, tables in REQUIRED_TABLES.items():
    db_path = ROOT / db

    if not db_path.exists():
        continue

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    results["tables"][db] = {}

    for table in tables:
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,)
        )

        found = cur.fetchone() is not None
        results["tables"][db][table] = found

        if found:
            pass_count += 1

            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]

                results["counts"][f"{db}:{table}"] = count

            except Exception as e:
                results["counts"][f"{db}:{table}"] = str(e)

        else:
            fail_count += 1

    conn.close()

results["summary"] = {
    "pass": pass_count,
    "fail": fail_count,
    "status": "PASS" if fail_count == 0 else "NEEDS_REVIEW"
}

print("\n========== OMEGA PRODUCTION AUDIT ==========\n")
print(json.dumps(results, indent=2))
print("\n===========================================\n")
