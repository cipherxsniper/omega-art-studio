import psycopg2

DB_CONFIG = {
    "dbname": "omega_bank",
    "user": "omega",
    "host": "localhost",
    "port": 5432
}

def reconcile():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        SELECT w.wallet_id,
               w.balance AS projected,
               COALESCE(SUM(
                   CASE WHEN e.payload->>'type'='CREDIT' THEN (e.payload->>'amount')::numeric
                        WHEN e.payload->>'type'='DEBIT' THEN -(e.payload->>'amount')::numeric
                        ELSE 0 END
               ),0) AS ledger
        FROM wallet_state_projection w
        LEFT JOIN ledger_events e
        ON w.wallet_id = e.aggregate_id
        GROUP BY w.wallet_id, w.balance
        HAVING w.balance != COALESCE(SUM(
            CASE WHEN e.payload->>'type'='CREDIT' THEN (e.payload->>'amount')::numeric
                 WHEN e.payload->>'type'='DEBIT' THEN -(e.payload->>'amount')::numeric
                 ELSE 0 END
        ),0)
    """)

    drift = cur.fetchall()

    print("\nDRIFT REPORT:")
    for row in drift:
        print(row)

    conn.close()

    return len(drift)
