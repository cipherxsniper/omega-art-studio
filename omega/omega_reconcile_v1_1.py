import psycopg2

DB_CONFIG = {
    "dbname": "omega_bank",
    "user": "omega",
    "password": "omega",
    "host": "localhost"
}

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

cur.execute("""
SELECT
    SUM(settled_balance) as liabilities,
    SUM(reserved_balance) as reserved
FROM wallets
""")

liab, res = cur.fetchone()

cur.execute("""
SELECT SUM(total_capital)
FROM treasury_reserve
""")

treasury = cur.fetchone()[0]

print("TREASURY:", treasury)
print("LIABILITIES:", liab)
print("RESERVED:", res)

if liab + res > treasury:
    print("❌ DRIFT DETECTED")
else:
    print("✅ SYSTEM CONSISTENT")

conn.close()
