import psycopg2

DB = {"dbname":"omega_bank","user":"omega"}

conn = psycopg2.connect(**DB)
cur = conn.cursor()

cur.execute("""
SELECT wallet_id,
       SUM(available_balance) as projected
FROM wallet_state_projection
GROUP BY wallet_id
""")

projection = dict(cur.fetchall())

cur.execute("""
SELECT aggregate_id,
       SUM(CASE WHEN event_type='CREDIT' THEN (payload->>'amount')::numeric
                WHEN event_type='DEBIT' THEN -(payload->>'amount')::numeric
                ELSE 0 END)
FROM ledger_events
GROUP BY aggregate_id
""")

ledger = dict(cur.fetchall())

print("=== DRIFT REPORT ===")
for k in ledger:
    p = float(projection.get(k, 0))
    l = float(ledger.get(k, 0))
    print(k, "DRIFT:", round(p - l, 2))

conn.close()
