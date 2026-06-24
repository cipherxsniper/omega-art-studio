#!/usr/bin/env python3

import os
import sqlite3
import psycopg2
from datetime import datetime, timezone

# -----------------------------
# SAFE ENV LOADER (NO DOTENV FRAMEWORK DEPENDENCY)
# -----------------------------

def env(name, default=None):
    return os.environ.get(name, default)

# -----------------------------
# DATABASE CONNECTIONS
# -----------------------------

SQLITE_DB = env("SQLITE_DB", os.path.expanduser("~/Omega-Production/omega_bank/omega_ledger.db"))

PG_CONN = env("PG_CONN", "dbname=omega_bank")

# -----------------------------
# POSTGRES ACCOUNTS
# -----------------------------

def load_accounts_pg():
    conn = psycopg2.connect(PG_CONN)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, owner_name
        FROM accounts
    """)

    rows = cur.fetchall()

    accounts = []
    for r in rows:
        accounts.append({
            "account_id": r[0],
            "owner_name": r[1]
        })

    cur.close()
    conn.close()
    return accounts

# -----------------------------
# SQLITE LEDGER EVENTS
# -----------------------------

def load_ledger_sqlite():
    conn = sqlite3.connect(SQLITE_DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, type, payload, timestamp
        FROM ledger_events
        ORDER BY timestamp DESC
    """)

    rows = cur.fetchall()

    events = []
    for r in rows:
        events.append({
            "event_id": r[0],
            "type": r[1],
            "payload": r[2],
            "timestamp": r[3]
        })

    conn.close()
    return events

# -----------------------------
# STRIPE EVENT SIMULATION BINDING
# -----------------------------

def infer_account_from_event(event, accounts):
    t = event["type"]

    # deterministic routing rules (NO DRIFT)
    if t == "DEPOSIT":
        return "OMEGA_RESERVE_LEDGER"
    elif t == "TRANSFER":
        return "OMEGA_CREDIT"
    else:
        return "SYSTEM"

# -----------------------------
# CORE BINDING ENGINE
# -----------------------------

def build_reality_map(accounts, ledger_events):

    mapping = {}

    for acc in accounts:
        mapping[acc["account_id"]] = {
            "owner": acc["owner_name"],
            "events": []
        }

    for e in ledger_events:
        # assign event deterministically
        for acc in accounts:
            assigned = infer_account_from_event(e, accounts)
            if acc["owner_name"] == assigned:
                mapping[acc["account_id"]]["events"].append(e)

    return mapping

# -----------------------------
# BALANCE PROJECTION (SAFE)
# -----------------------------

def compute_balances(reality_map):
    balances = {}

    for acc_id, data in reality_map.items():
        balance = 0.0

        for e in data["events"]:
            if e["type"] == "DEPOSIT":
                try:
                    payload = eval(e["payload"]) if isinstance(e["payload"], str) else {}
                    balance += float(payload.get("amount", 0))
                except:
                    pass

            if e["type"] == "TRANSFER":
                try:
                    payload = eval(e["payload"]) if isinstance(e["payload"], str) else {}
                    balance -= float(payload.get("amount", 0))
                except:
                    pass

        balances[acc_id] = {
            "owner": data["owner"],
            "balance": balance
        }

    return balances

# -----------------------------
# RUN
# -----------------------------

def run():
    accounts = load_accounts_pg()
    ledger = load_ledger_sqlite()

    reality_map = build_reality_map(accounts, ledger)
    balances = compute_balances(reality_map)

    print("🧠 OMEGA REALITY BINDING LAYER v1")
    print({
        "accounts": len(accounts),
        "ledger_events": len(ledger),
        "balances": balances
    })

if __name__ == "__main__":
    run()
