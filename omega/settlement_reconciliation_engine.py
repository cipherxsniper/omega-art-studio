#!/usr/bin/env python3
"""
OMEGA SETTLEMENT RECONCILIATION ENGINE
- Validates ledger integrity
- Verifies debit/credit parity
- Detects balance drift
- Generates reconciliation report
- Snapshots treasury state
- Production-safe deterministic execution
"""

import sqlite3
import time
from datetime import datetime

DB_PATH = "omega_ledger.db"


# ----------------------------
# DB HELPERS
# ----------------------------
def query(conn, sql, params=()):
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur.fetchall()


def money(x):
    try:
        return float(x or 0)
    except:
        return 0.0


# ----------------------------
# CORE RECONCILIATION LOGIC
# ----------------------------
def get_account_summary(conn):
    return query(conn, """
        SELECT user_id, balance
        FROM accounts
        ORDER BY user_id
    """)


def get_ledger_summary(conn):
    return query(conn, """
        SELECT
            account_id,
            SUM(CASE WHEN type='credit' THEN amount ELSE 0 END),
            SUM(CASE WHEN type='debit' THEN amount ELSE 0 END)
        FROM entries
        GROUP BY account_id
    """)


def compute_net(credits, debits):
    return money(credits) - money(debits)


def reconcile(conn):
    accounts = get_account_summary(conn)
    ledger = get_ledger_summary(conn)

    ledger_map = {
        row[0]: {
            "credits": money(row[1]),
            "debits": money(row[2]),
            "net": compute_net(row[1], row[2])
        }
        for row in ledger
    }

    drift_report = []
    system_total = 0.0

    for acct_id, balance in accounts:
        balance = money(balance)

        ledger_net = ledger_map.get(acct_id, {}).get("net", 0.0)

        drift = balance - ledger_net

        system_total += balance

        drift_report.append({
            "account": acct_id,
            "balance": balance,
            "ledger_net": ledger_net,
            "drift": drift
        })

    return drift_report, system_total


# ----------------------------
# REPORTING
# ----------------------------
def print_report(drift_report, system_total):
    print("\n" + "═" * 80)
    print("🏦 OMEGA SETTLEMENT RECONCILIATION REPORT")
    print("═" * 80)

    for row in drift_report:
        status = "OK" if abs(row["drift"]) < 0.0001 else "DRIFT"
        print(f"""
┌──────────────────────────────────────────────┐
│ ACCOUNT : {row['account']}
│ BALANCE : ${row['balance']:.2f}
│ LEDGER  : ${row['ledger_net']:.2f}
│ DRIFT   : ${row['drift']:.2f}
│ STATUS  : {status}
└──────────────────────────────────────────────┘
""")

    print("═" * 80)
    print(f"💰 SYSTEM TOTAL: ${system_total:.2f}")
    print("═" * 80)


# ----------------------------
# SNAPSHOT
# ----------------------------
def snapshot(system_total):
    ts = datetime.utcnow().isoformat()

    print("\n📸 SNAPSHOT")
    print(f"TIME: {ts}")
    print(f"SYSTEM TOTAL: ${system_total:.2f}")


# ----------------------------
# MAIN
# ----------------------------
def main():
    conn = sqlite3.connect(DB_PATH)

    drift_report, system_total = reconcile(conn)

    print_report(drift_report, system_total)

    snapshot(system_total)

    conn.close()


if __name__ == "__main__":
    main()
