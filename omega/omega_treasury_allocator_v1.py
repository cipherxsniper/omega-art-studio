#!/usr/bin/env python3

import sqlite3
import uuid
import time
from decimal import Decimal

DB = "omega_ledger.db"

ALLOC = {
    "OMEGA_RESERVE": Decimal("0.40"),
    "OMEGA_INVESTMENT": Decimal("0.30"),
    "OMEGA_CREDIT": Decimal("0.20"),
    "THOMAS_LH": Decimal("0.10")
}

TREASURY_SURPLUS = Decimal("1000000.00")


def connect():
    return sqlite3.connect(DB)


def insert(cur, account_id, event_type, amount, tx_id):

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


conn = connect()
cur = conn.cursor()

tx_id = f"TREASURY_ALLOC_{uuid.uuid4().hex[:10]}"

for account, ratio in ALLOC.items():

    amount = TREASURY_SURPLUS * ratio

    insert(
        cur,
        account,
        "TREASURY_ALLOCATION_CREDIT",
        amount,
        tx_id
    )

    insert(
        cur,
        "OMEGA_TREASURY",
        "TREASURY_ALLOCATION_DEBIT",
        amount,
        tx_id
    )

conn.commit()

print("\n=== TREASURY ALLOCATION COMPLETE ===")
print("TX_ID:", tx_id)

conn.close()
