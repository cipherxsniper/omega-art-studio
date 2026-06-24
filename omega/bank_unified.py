
#!/usr/bin/env python3

import json
from decimal import Decimal
from pathlib import Path

BASE = Path("~/Omega-Production/omega_bank").expanduser()

def load_json(path):
    try:
        return json.loads(Path(path).read_text())
    except:
        return []

def safe_decimal(x):
    try:
        return Decimal(str(x))
    except:
        return Decimal("0")

# -----------------------------
# LAYER 1: LEDGER DB OUTPUT
# -----------------------------
ledger_file = BASE / "omega_bank.db"

ledger_total = Decimal("0")
try:
    import sqlite3
    conn = sqlite3.connect(str(ledger_file))
    cur = conn.cursor()

    cur.execute("""
        SELECT COALESCE(SUM(
            CASE WHEN direction='CREDIT' THEN amount
                 WHEN direction='DEBIT' THEN -amount
                 ELSE 0 END
        ), 0)
        FROM ledger_entries
    """)

    ledger_total = safe_decimal(cur.fetchone()[0])
except:
    pass

# -----------------------------
# LAYER 2: WALLET REGISTRY
# -----------------------------
wallets = load_json(BASE / "omega_wallets.json")
wallet_total = sum(safe_decimal(w.get("balance", 0)) for w in wallets)

# -----------------------------
# LAYER 3: ACCOUNT REGISTRY
# -----------------------------
accounts = load_json(BASE / "omega_accounts.json")
account_total = sum(safe_decimal(a.get("balance", 0)) for a in accounts)

# -----------------------------
# FINAL CONSOLIDATION
# -----------------------------
total = ledger_total + wallet_total + account_total

print("\n🏦 OMEGA UNIFIED FINANCIAL NETWORK")
print("────────────────────────────────────")
print(f"📒 Ledger Layer  : ${ledger_total:.2f} USD")
print(f"👛 Wallet Layer  : ${wallet_total:.2f} USD")
print(f"🏦 Account Layer : ${account_total:.2f} USD")
print("────────────────────────────────────")
print(f"💎 TOTAL OMEGA   : ${total:.2f} USD")
print("────────────────────────────────────\n")

