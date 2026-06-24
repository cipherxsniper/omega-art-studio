#!/usr/bin/env python3

import sqlite3
import json
import uuid
from datetime import datetime, timezone

DB_PATH = "omega_ledger.db"

CAPITALIZATION_EVENT = {
    "event_id": str(uuid.uuid4()),
    "type": "CAPITALIZATION_SYSTEM_INIT",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "currency": "USD",
    "source": "OMEGA_SYSTEM",

    # Canonical system-wide exposure
    "treasury_exposure": "-13300000000 USD",

    # Deterministic allocations (must sum logically to exposure distribution model)
    "allocations": {
        "OMEGA_CREDIT": "600000000 USD",
        "OMEGA_RESERVE": "750000000 USD",
        "OMEGA_INVESTMENT": "250000000 USD",
        "THOMAS_LH": "50000000 USD",
        "SYSTEM_TREASURY": "-13300000000 USD"
    },

    "note": "Canonical initialization event for Omega financial system state"
}


def ensure_tables(cur):
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ledger_events (
        id TEXT PRIMARY KEY,
        type TEXT,
        payload TEXT,
        timestamp TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        balance REAL DEFAULT 0
    )
    """)


def seed_accounts(cur):
    accounts = [
        ("TREASURY", "OMEGA_TREASURY"),
        ("CREDIT", "OMEGA_CREDIT"),
        ("RESERVE", "OMEGA_RESERVE"),
        ("INVESTMENT", "OMEGA_INVESTMENT"),
        ("THOMAS", "THOMAS_LH")
    ]

    for acc_id, user in accounts:
        cur.execute("""
        INSERT OR IGNORE INTO accounts (id, user_id, balance)
        VALUES (?, ?, 0.0)
        """, (acc_id, user))


def insert_event(cur):
    cur.execute("""
    INSERT INTO ledger_events (id, type, payload, timestamp)
    VALUES (?, ?, ?, ?)
    """, (
        CAPITALIZATION_EVENT["event_id"],
        CAPITALIZATION_EVENT["type"],
        json.dumps(CAPITALIZATION_EVENT),
        CAPITALIZATION_EVENT["timestamp"]
    ))


def derive_balances(cur):
    cur.execute("SELECT payload FROM ledger_events")
    events = cur.fetchall()

    balances = {
        "OMEGA_CREDIT": 0,
        "OMEGA_RESERVE": 0,
        "OMEGA_INVESTMENT": 0,
        "THOMAS_LH": 0,
        "SYSTEM_TREASURY": 0
    }

    for (payload,) in events:
        data = json.loads(payload)

        if data.get("type") == "CAPITALIZATION_SYSTEM_INIT":
            alloc = data["allocations"]

            for k, v in alloc.items():
                amount = float(v.replace(" USD", "").replace(",", ""))
                balances[k] = amount

    return balances


def apply_balances(cur, balances):
    mapping = {
        "OMEGA_CREDIT": "OMEGA_CREDIT",
        "OMEGA_RESERVE": "OMEGA_RESERVE",
        "OMEGA_INVESTMENT": "OMEGA_INVESTMENT",
        "THOMAS_LH": "THOMAS_LH",
        "SYSTEM_TREASURY": "OMEGA_TREASURY"
    }

    for key, value in balances.items():
        if key in mapping:
            cur.execute("""
            UPDATE accounts
            SET balance = ?
            WHERE user_id = ?
            """, (value, mapping[key]))


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    ensure_tables(cur)
    seed_accounts(cur)
    insert_event(cur)

    balances = derive_balances(cur)
    apply_balances(cur, balances)

    conn.commit()
    conn.close()

    print("🧠 CAPITALIZATION INIT COMPLETE")
    print(json.dumps(balances, indent=2))


if __name__ == "__main__":
    run()
