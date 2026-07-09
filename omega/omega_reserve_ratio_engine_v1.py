#!/usr/bin/env python3

import sqlite3
from decimal import Decimal

DB = "omega_ledger.db"

conn = sqlite3.connect(DB)

rows = conn.execute("""
SELECT account_id, balance
FROM accounts
""").fetchall()

balances = {r[0]: Decimal(str(r[1])) for r in rows}

reserve = balances.get("OMEGA_RESERVE", Decimal("0"))
treasury = balances.get("OMEGA_TREASURY", Decimal("1"))

ratio = (reserve / treasury) * Decimal("100")

print("\n=== RESERVE RATIO ENGINE ===")
print(f"RESERVE : ${reserve:,.2f}")
print(f"TREASURY: ${treasury:,.2f}")
print(f"RATIO   : {ratio:.2f}%")

conn.close()
