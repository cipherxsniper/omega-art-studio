import sqlite3

DB = "omega_ledger.db"

WIDTH = 78

def divider():
    return "═" * WIDTH

def section(title):
    print("\n" + divider())
    print(f" {title}")
    print(divider())

def account_box(account_id, user, balance):
    print("┌" + "─" * 62 + "┐")
    print(f"│ ACCOUNT : {account_id:<51}│")
    print(f"│ USER    : {user:<51}│")
    print(f"│ BALANCE : ${balance:>49,.2f} │")
    print("└" + "─" * 62 + "┘")

conn = sqlite3.connect(DB)
cur = conn.cursor()

# ONLY SHOW REAL FUNDED ACCOUNTS
FUNDED = [
    "OMEGA_TREASURY",
    "OMEGA_CREDIT",
    "OMEGA_RESERVE",
    "OMEGA_INVESTMENT",
    "THOMAS_LH"
]

section("🏦 OMEGA ACCOUNT LEDGER")

for user_id in FUNDED:
    cur.execute("""
        SELECT id, user_id, balance
        FROM accounts
        WHERE user_id = ?
    """, (user_id,))

    row = cur.fetchone()

    if row:
        account_box(
            row[0],
            row[1],
            row[2]
        )

section("📒 LEDGER SUMMARY")

cur.execute("""
SELECT
    tx_type,
    COUNT(*),
    SUM(amount)
FROM ledger
GROUP BY tx_type
ORDER BY tx_type
""")

ledger_rows = cur.fetchall()

for tx_type, count, total in ledger_rows:

    total = total or 0

    print(
        f"{str(tx_type):<32} "
        f"COUNT={count:<8} "
        f"TOTAL=${total:,.2f}"
    )

section("💰 SYSTEM TOTAL")

cur.execute("""
SELECT SUM(balance)
FROM accounts
WHERE user_id IN (
    'OMEGA_TREASURY',
    'OMEGA_CREDIT',
    'OMEGA_RESERVE',
    'OMEGA_INVESTMENT',
    'THOMAS_LH'
)
""")

total = cur.fetchone()[0] or 0

print(f"\n NET BALANCE : ${total:,.2f}\n")

conn.close()
