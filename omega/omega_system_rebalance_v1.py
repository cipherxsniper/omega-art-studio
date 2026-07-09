#!/usr/bin/env python3

import sqlite3
import uuid
import time
from decimal import Decimal, ROUND_HALF_UP

DB = "omega_ledger.db"

TARGET_TOTAL = Decimal("56000000000.00")

EXCLUDED = {
    "OMEGA_SYSTEM_CAPITAL"
}


def D(v):
    return Decimal(str(v)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


def connect():
    return sqlite3.connect(DB)


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

        if account_id in EXCLUDED:
            continue

        if account_id not in balances:
            balances[account_id] = Decimal("0")

        amount = D(amount)

        et = str(event_type).lower()

        if "credit" in et:
            balances[account_id] += amount

        elif "debit" in et:
            balances[account_id] -= amount

        else:
            balances[account_id] += amount

    return balances


def insert_event(cur, account_id, event_type, amount, tx_id):

    cur.execute("""
        INSERT INTO ledger_events (
            account_id,
            event_type,
            amount,
            tx_id,
            timestamp
        ) VALUES (?, ?, ?, ?, ?)
    """, (
        account_id,
        event_type,
        float(amount),
        tx_id,
        time.time()
    ))


def finalize(cur, tx_id):

    cur.execute("""
        INSERT INTO finalized_events (
            event_id,
            hash,
            prev_hash,
            timestamp
        ) VALUES (?, ?, ?, ?)
    """, (
        tx_id,
        str(uuid.uuid4()),
        "OMEGA_REBALANCE_V1",
        time.time()
    ))


def main():

    conn = connect()
    cur = conn.cursor()

    balances = compute_balances(conn)

    accounts = sorted(list(balances.keys()))

    print("\n=== OMEGA SYSTEM REBALANCE V1 ===\n")

    if not accounts:
        print("NO ACCOUNTS FOUND")
        return

    target_each = (
        TARGET_TOTAL / Decimal(str(len(accounts)))
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    print(f"TARGET TOTAL : ${TARGET_TOTAL:,.2f}")
    print(f"ACCOUNT COUNT: {len(accounts)}")
    print(f"TARGET EACH  : ${target_each:,.2f}\n")

    tx_id = f"REBALANCE_{uuid.uuid4().hex[:12]}"

    for account_id in accounts:

        current = D(balances[account_id])

        delta = target_each - current

        if abs(delta) < Decimal("0.01"):
            continue

        if delta > 0:

            insert_event(
                cur,
                account_id,
                "SYSTEM_REBALANCE_CREDIT",
                delta,
                tx_id
            )

            insert_event(
                cur,
                "OMEGA_SYSTEM_CAPITAL",
                "SYSTEM_REBALANCE_DEBIT",
                delta,
                tx_id
            )

        else:

            delta_abs = abs(delta)

            insert_event(
                cur,
                account_id,
                "SYSTEM_REBALANCE_DEBIT",
                delta_abs,
                tx_id
            )

            insert_event(
                cur,
                "OMEGA_SYSTEM_CAPITAL",
                "SYSTEM_REBALANCE_CREDIT",
                delta_abs,
                tx_id
            )

        print(
            f"{account_id:<24} "
            f"OLD=${current:>15,.2f} "
            f"NEW=${target_each:>15,.2f}"
        )

    finalize(cur, tx_id)

    conn.commit()

    print("\n══════════════════════════════════════")
    print("SYSTEM REBALANCE COMPLETE")
    print(f"TX_ID : {tx_id}")
    print("══════════════════════════════════════\n")

    conn.close()


if __name__ == "__main__":
    main()
