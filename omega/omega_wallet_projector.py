import psycopg2

DB_CONFIG = {
    "dbname": "omega_bank",
    "user": "omega",
    "host": "localhost",
    "port": 5432
}

def rebuild_wallet(wallet_id):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        SELECT payload
        FROM ledger_events
        WHERE aggregate_id = %s
        ORDER BY created_at ASC
    """, (wallet_id,))

    events = cur.fetchall()

    balance = 0

    for (payload,) in events:
        data = payload
        if isinstance(payload, str):
            import json
            data = json.loads(payload)

        if data.get("type") == "CREDIT":
            balance += float(data["amount"])
        elif data.get("type") == "DEBIT":
            balance -= float(data["amount"])

    cur.execute("""
        UPDATE wallet_state_projection
        SET balance = %s
        WHERE wallet_id = %s
    """, (balance, wallet_id))

    conn.commit()
    cur.close()
    conn.close()

    return balance
