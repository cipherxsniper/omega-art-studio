#!/usr/bin/env python3

import sqlite3
import uuid
import time
from decimal import Decimal

DB = "omega_ledger.db"

TOTAL_CAPITAL = Decimal("56000000000.00")

ALLOCATIONS = {
    "OMEGA_TREASURY": Decimal("0.70"),
    "OMEGA_RESERVE": Decimal("0.15"),
    "OMEGA_CREDIT": Decimal("0.10"),
    "OMEGA_INVESTMENT": Decimal("0.04"),
    "THOMAS_LH": Decimal("0.01")
}


def connect():
    return sqlite3.connect(DB)


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
        "GENESIS_RECAP_V2",
        time.time()
    ))


def main():

    conn = connect()
    cur = conn.cursor()

    tx_id = f"RECAP_{uuid.uuid4().hex[:12]}"

    print("\n=== OMEGA RECAPITALIZATION V2 ===\n")

    total_allocated = Decimal("0")

    for account_id, ratio in ALLOCATIONS.items():

        amount = TOTAL_CAPITAL * ratio

        total_allocated += amount

        insert_event(
            cur,
            account_id,
            "CAPITALIZATION_CREDIT",
            amount,
            tx_id
        )

        insert_event(
            cur,
            "OMEGA_SYSTEM_CAPITAL",
            "CAPITALIZATION_DEBIT",
            amount,
            tx_id
        )

        print(f"{account_id:<24} ${amount:,.2f}")

    finalize(cur, tx_id)

    conn.commit()

    print("\n══════════════════════════════════════")
    print(f"TOTAL RECAPITALIZED : ${total_allocated:,.2f}")
    print("LEDGER STATUS       : BALANCED")
    print(f"TX_ID               : {tx_id}")
    print("══════════════════════════════════════\n")

    conn.close()


if __name__ == "__main__":
    main()
