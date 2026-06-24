#!/usr/bin/env python3

import sqlite3
from decimal import Decimal

DB = "omega_ledger.db"


def D(v):
    return Decimal(str(v))


conn = sqlite3.connect(DB)

rows = conn.execute("""
SELECT
    account_id,
    event_type,
    amount
FROM ledger_events
""").fetchall()

revenue = Decimal("0")
expense = Decimal("0")

for account_id, event_type, amount in rows:

    amount = D(amount)

    et = str(event_type).lower()

    if "revenue" in et:
        revenue += amount

    if "expense" in et:
        expense += amount

profit = revenue - expense

print("\n=== OMEGA PROFIT & LOSS ===")
print(f"REVENUE : ${revenue:,.2f}")
print(f"EXPENSE : ${expense:,.2f}")
print(f"NET P&L : ${profit:,.2f}")

conn.close()
