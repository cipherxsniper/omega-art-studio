#!/usr/bin/env python3

import sqlite3
import time
from decimal import Decimal

BILLING_DB = "billing.db"
LEDGER_DB = "omega_ledger.db"

THOMAS_ACCOUNT = "THOMAS_LH"
TREASURY_ACCOUNT = "OMEGA_TREASURY"

SYSTEM_CAPITALIZATION = Decimal("57000000000.00")


def connect(db):
    return sqlite3.connect(db)


def safe_decimal(value):
    try:
        return Decimal(str(value))
    except:
        return Decimal("0")


def fetch_subscriptions(conn):
    try:
        rows = conn.execute("""
            SELECT
                subscription_id,
                customer_id,
                status,
                price_id
            FROM subscriptions
        """).fetchall()

        return rows

    except Exception as e:
        print("[SUBSCRIPTION FETCH ERROR]", str(e))
        return []


def fetch_ledger_totals(conn):
    try:
        rows = conn.execute("""
            SELECT
                account_id,
                type,
                amount
            FROM ledger_events
        """).fetchall()

        totals = {}

        for account_id, tx_type, amount in rows:

            amount = safe_decimal(amount)

            if account_id not in totals:
                totals[account_id] = Decimal("0")

            if tx_type.lower() == "credit":
                totals[account_id] += amount

            elif tx_type.lower() == "debit":
                totals[account_id] -= amount

        return totals

    except Exception as e:
        print("[LEDGER FETCH ERROR]", str(e))
        return {}


def compute_mrr(subscriptions):

    price_map = {
        "price_1TXZ72A5xsR4lvM4aVLVFJAW": Decimal("97"),
        "price_1TXZ8RA5xsR4lvM4AMoEXTGs": Decimal("497"),
        "price_1TXZ9DA5xsR4lvM47e8aC560": Decimal("1497"),
    }

    total = Decimal("0")

    for sub in subscriptions:

        _, _, status, price_id = sub

        if status != "active":
            continue

        total += price_map.get(price_id, Decimal("0"))

    return total


def reconcile():

    print("\n=== OMEGA FINAL RECONCILIATION ===\n")

    billing_conn = connect(BILLING_DB)
    ledger_conn = connect(LEDGER_DB)

    subscriptions = fetch_subscriptions(billing_conn)

    ledger_totals = fetch_ledger_totals(ledger_conn)

    mrr = compute_mrr(subscriptions)

    treasury_balance = ledger_totals.get(
        TREASURY_ACCOUNT,
        Decimal("0")
    )

    thomas_balance = ledger_totals.get(
        THOMAS_ACCOUNT,
        Decimal("0")
    )

    system_total = Decimal("0")

    for _, balance in ledger_totals.items():
        system_total += balance

    drift = SYSTEM_CAPITALIZATION - system_total

    print("ACTIVE SUBSCRIPTIONS :", len(subscriptions))
    print("MONTHLY RECURRING REV:", f"${mrr:,.2f}")

    print("\n=== ACCOUNT TOTALS ===\n")

    for account, balance in ledger_totals.items():
        print(f"{account:<24} ${balance:,.2f}")

    print("\n=== CORE CAPITAL ===\n")

    print("TREASURY BALANCE :", f"${treasury_balance:,.2f}")
    print("THOMAS BALANCE   :", f"${thomas_balance:,.2f}")

    print("\n=== SYSTEM STATE ===\n")

    print("EXPECTED CAPITAL :", f"${SYSTEM_CAPITALIZATION:,.2f}")
    print("LEDGER TOTAL     :", f"${system_total:,.2f}")
    print("DRIFT            :", f"${drift:,.2f}")

    balanced = drift == Decimal("0")

    print("BALANCED         :", balanced)

    billing_conn.close()
    ledger_conn.close()

    print("\n=== RECONCILIATION COMPLETE ===\n")


if __name__ == "__main__":
    reconcile()
