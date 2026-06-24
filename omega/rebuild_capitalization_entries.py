#!/usr/bin/env python3

import sqlite3
import uuid
import time

DB = "omega_ledger.db"

ALLOCATIONS = {
    "OMEGA_TREASURY": 24850000000.00,
    "OMEGA_CREDIT": 600000000.00,
    "OMEGA_RESERVE": 750000000.00,
    "OMEGA_INVESTMENT": 250000000.00,
    "THOMAS_LH": 550000000.00
}

conn = sqlite3.connect(DB)
cur = conn.cursor()

master_tx = f"capitalization_{uuid.uuid4().hex[:12]}"
ts = time.time()

total = 0

for account, amount in ALLOCATIONS.items():

    total += amount

    debit_id = str(uuid.uuid4())
    credit_id = str(uuid.uuid4())

    cur.execute("""
    INSERT INTO entries (
        id,
        tx_id,
        account_id,
        type,
        amount,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        debit_id,
        master_tx,
        "OMEGA_ISSUANCE",
        "debit",
        amount,
        ts
    ))

    cur.execute("""
    INSERT INTO entries (
        id,
        tx_id,
        account_id,
        type,
        amount,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        credit_id,
        master_tx,
        account,
        "credit",
        amount,
        ts
    ))

cur.execute("""
INSERT INTO ledger (
    id,
    tx_type,
    amount,
    status
)
VALUES (?, ?, ?, ?)
""", (
    master_tx,
    "CAPITALIZATION_RECONSTRUCTION",
    total,
    "SETTLED"
))

conn.commit()
conn.close()

print()
print("[CAPITALIZATION RECONSTRUCTION COMPLETE]")
print(f"TOTAL ISSUED: ${total:,.2f}")
print()
