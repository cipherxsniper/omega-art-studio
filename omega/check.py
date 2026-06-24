import sqlite3

DB = "omega_ledger.db"

def money(x):
    return f"${x:,.2f}" if x is not None else "$0.00"

def safe(x):
    return "UNCLASSIFIED" if x is None else str(x)

def line():
    return "═" * 78

conn = sqlite3.connect(DB)
cur = conn.cursor()

print("\n🏦 OMEGA FINANCIAL CONTROL SYSTEM")
print(line())

print("\n📌 ACCOUNTS\n" + line())

for row in cur.execute("SELECT id, user_id, balance FROM accounts"):
    print(f"""
┌──────────────────────────────────────────────┐
│ ID     : {row[0]}
│ USER   : {row[1]}
│ BALANCE: {money(row[2])}
└──────────────────────────────────────────────┘
""")

print("\n📒 LEDGER SUMMARY\n" + line())

for row in cur.execute("""
    SELECT tx_type,
           COUNT(*),
           COALESCE(SUM(amount), 0)
    FROM ledger
    GROUP BY tx_type
"""):
    tx_type = safe(row[0])
    count = row[1] or 0
    total = row[2] or 0

    print(f"{tx_type:<30} COUNT={count:<8} TOTAL={money(total)}")

print("\n💰 SYSTEM TOTAL\n" + line())

total = cur.execute("SELECT COALESCE(SUM(balance),0) FROM accounts").fetchone()[0]
print(f"NET BALANCE : {money(total)}")

conn.close()
