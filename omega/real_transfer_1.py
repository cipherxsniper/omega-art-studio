#!/usr/bin/env python3

import sqlite3
import sys
import uuid
import time

DB = "omega_ledger.db"

if len(sys.argv) != 4:
    print("USAGE:")
    print("python real_transfer.py FROM_USER TO_USER AMOUNT")
    print("example:")
    print("python real_transfer.py THOMAS_LH OMEGA_TREASURY 500000000")
    sys.exit(1)

FROM_USER = sys.argv[1].strip()
TO_USER = sys.argv[2].strip()
AMOUNT = float(sys.argv[3])

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
SELECT id, balance
FROM accounts
WHERE user_id = ?
""", (FROM_USER,))
from_row = cur.fetchone()

cur.execute("""
SELECT id, balance
FROM accounts
WHERE user_id = ?
""", (TO_USER,))
to_row = cur.fetchone()

if not from_row:
    print(f"[ERROR] FROM ACCOUNT NOT FOUND: {FROM_USER}")
    sys.exit(1)

if not to_row:
    print(f"[ERROR] TO ACCOUNT NOT FOUND: {TO_USER}")
    sys.exit(1)

from_id, from_balance = from_row
to_id, to_balance = to_row

if from_balance < AMOUNT:
    print("[ERROR] INSUFFICIENT FUNDS")
    print("AVAILABLE:", from_balance)
    print("REQUESTED:", AMOUNT)
    sys.exit(1)

new_from_balance = from_balance - AMOUNT
new_to_balance = to_balance + AMOUNT

cur.execute("""
UPDATE accounts
SET balance = ?
WHERE user_id = ?
""", (new_from_balance, FROM_USER))

cur.execute("""
UPDATE accounts
SET balance = ?
WHERE user_id = ?
""", (new_to_balance, TO_USER))

tx_id = f"tx_{uuid.uuid4().hex[:16]}"
ts = time.time()

debit_entry = str(uuid.uuid4())
credit_entry = str(uuid.uuid4())

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
    debit_entry,
    tx_id,
    FROM_USER,
    "debit",
    AMOUNT,
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
    credit_entry,
    tx_id,
    TO_USER,
    "credit",
    AMOUNT,
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
    tx_id,
    f"REAL_TRANSFER::{FROM_USER}_TO_{TO_USER}",
    AMOUNT,
    "SETTLED"
))

cur.execute("""
INSERT INTO ledger_events (
    event_id,
    event_hash,
    event_type,
    payload,
    created_at
)
VALUES (?, ?, ?, ?, datetime('now'))
""", (
    tx_id,
    uuid.uuid4().hex,
    "REAL_TRANSFER",
    f"{FROM_USER}->{TO_USER}:${AMOUNT}"
))

conn.commit()

print()
print("========================================================")
print("        OMEGA REAL FUNDS TRANSFER COMPLETE")
print("========================================================")
print()
print(f"FROM     : {FROM_USER}")
print(f"TO       : {TO_USER}")
print(f"AMOUNT   : ${AMOUNT:,.2f}")
print()
print(f"{FROM_USER} NEW BALANCE : ${new_from_balance:,.2f}")
print(f"{TO_USER} NEW BALANCE   : ${new_to_balance:,.2f}")
print()
print(f"TX ID : {tx_id}")
print()
print("RECORDED INTO:")
print("- accounts")
print("- entries")
print("- ledger")
print("- ledger_events")
print()
print("STATUS : SETTLED")
print("========================================================")

conn.close()
