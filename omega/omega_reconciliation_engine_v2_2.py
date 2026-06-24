#!/usr/bin/env python3

import sqlite3
from decimal import Decimal

LEDGER_DB = "omega_ledger.db"

TREASURY = "OMEGA_TREASURY"
CREDIT = "OMEGA_CREDIT"
RESERVE = "OMEGA_RESERVE"
INVESTMENT = "OMEGA_INVESTMENT"
THOMAS = "THOMAS_LH"


def d(v):
    try:
        return Decimal(str(v))
    except:
        return Decimal("0")


def connect():
    return sqlite3.connect(LEDGER_DB)


def compute_balances(conn):

    rows = conn.execute("""
        SELECT
            account_id,
            event_type,
            amount
        FROM ledger_events
    """).fetchall()

    balances = {}

    for account_id, event_type, amount in rows:

        amount = d(amount)

        if account_id not in balances:
            balances[account_id] = Decimal("0")

        et = str(event_type).lower()

        if "credit" in et:
            balances[account_id] += amount

        elif "debit" in et:
            balances[account_id] -= amount

        else:
            balances[account_id] += amount

    return balances


def print_balances(balances):

    print("\n🏦 OMEGA RECONCILIATION V2\n")

    total = Decimal("0")

    for account, balance in balances.items():

        total += balance

        print("┌──────────────────────────────────────────────┐")
        print(f"│ ACCOUNT : {account}")
        print(f"│ BALANCE : ${balance:,.2f} USD")
        print("└──────────────────────────────────────────────┘\n")

    print("══════════════════════════════════════════════")
    print(f"💰 SYSTEM TOTAL : ${total:,.2f}")
    print("══════════════════════════════════════════════")

    if abs(total) < Decimal("0.0001"):
        print("\n✅ LEDGER BALANCED\n")
    else:
        print("\n❌ LEDGER DRIFT DETECTED\n")


def subscription_summary(conn):

    try:

        rows = conn.execute("""
            SELECT
                customer_id,
                status,
                price_id
            FROM subscriptions
        """).fetchall()

        print("\n📦 SUBSCRIPTION SUMMARY\n")

        print(f"TOTAL SUBSCRIPTIONS : {len(rows)}\n")

        for row in rows:
            print(row)

    except Exception as e:
        print("[SUBSCRIPTION ERROR]", str(e))


def finalized_summary(conn):

    try:

        count = conn.execute("""
            SELECT COUNT(*)
            FROM finalized_events
        """).fetchone()[0]

        print("\n🔒 FINALIZED EVENTS")
        print("══════════════════════════════")
        print("TOTAL :", count)

    except Exception as e:
        print("[FINALIZATION ERROR]", str(e))


def main():

    conn = connect()

    balances = compute_balances(conn)

    print_balances(balances)

    subscription_summary(conn)

    finalized_summary(conn)

    conn.close()


if __name__ == "__main__":
    main()
