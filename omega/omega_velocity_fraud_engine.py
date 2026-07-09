#!/usr/bin/env python3

import psycopg2

DB_CONFIG = {
    "dbname": "omega_bank",
    "user": "omega",
    "password": "omega_pass",
    "host": "localhost"
}

MAX_TX_PER_WINDOW = 5
WINDOW_MINUTES = 5

conn = psycopg2.connect(**DB_CONFIG)

with conn:

    with conn.cursor() as cur:

        cur.execute(f"""
            SELECT
                wallet_id,
                COUNT(*) AS tx_count,
                SUM(amount) AS volume
            FROM payment_authorizations
            WHERE created_at >= NOW() - INTERVAL '{WINDOW_MINUTES} minutes'
            GROUP BY wallet_id
            HAVING COUNT(*) > {MAX_TX_PER_WINDOW}
        """)

        rows = cur.fetchall()

        for row in rows:

            wallet_id = row[0]
            tx_count = row[1]
            volume = row[2]

            print(
                f"FRAUD ALERT :: "
                f"{wallet_id} :: "
                f"{tx_count} tx :: "
                f"{volume}"
            )

            cur.execute("""
                UPDATE wallets
                SET status='FROZEN'
                WHERE id=%s
            """, (wallet_id,))

            print(f"WALLET FROZEN :: {wallet_id}")
