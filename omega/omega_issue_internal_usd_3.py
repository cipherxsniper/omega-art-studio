import psycopg2, json, uuid

DB = {"dbname":"omega_bank","user":"omega"}

def issue(wallet_id, amount):
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO ledger_events (
            event_type,
            aggregate_id,
            aggregate_type,
            payload,
            idempotency_key
        )
        VALUES (
            'CREDIT',
            %s,
            'WALLET',
            %s,
            %s
        )
    """, (
        wallet_id,
        json.dumps({"amount": float(amount), "currency": "OMEGA_USD"}),
        str(uuid.uuid4())
    ))

    conn.commit()
    conn.close()
    print("OMEGA_USD ISSUED (INTERNAL):", amount)

if __name__ == "__main__":
    import sys
    issue(sys.argv[1], sys.argv[2])
