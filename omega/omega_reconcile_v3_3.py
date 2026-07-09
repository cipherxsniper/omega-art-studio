import psycopg2

DB = {
    "dbname": "omega_bank",
    "user": "omega",
    "password": "omega",
    "host": "localhost"
}

conn = psycopg2.connect(**DB)
cur = conn.cursor()

cur.execute("""
SELECT
    SUM(settled_balance),
    SUM(reserved_balance),
    SUM(pending_balance)
FROM wallet_state_projection
""")

settled, reserved, pending = cur.fetchone()

cur.execute("""
SELECT SUM((payload->>'amount')::numeric)
FROM omega_events
WHERE event_type = 'AUTH_APPROVED'
""")

event_total = cur.fetchone()[0]

print("STATE SETTLED:", settled)
print("STATE RESERVED:", reserved)
print("EVENT TOTAL:", event_total)

if reserved != event_total:
    print("❌ DRIFT DETECTED")
else:
    print("✅ SYSTEM CONSISTENT")

conn.close()
