import psycopg2
import uuid

conn = psycopg2.connect(dbname="omega_bank", user="omega")

SYSTEM_ID = str(uuid.uuid4())

with conn.cursor() as cur:

    cur.execute("""
        INSERT INTO wallets (
            id,
            currency,
            settled_balance
        )
        VALUES (%s, %s, %s)
        ON CONFLICT (id) DO NOTHING
    """, (
        SYSTEM_ID,
        'USD',
        1000000000.00
    ))

conn.commit()
conn.close()

print("SYSTEM_WALLET_ID:", SYSTEM_ID)
