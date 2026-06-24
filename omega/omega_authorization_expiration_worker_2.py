#!/usr/bin/env python3

import time
import psycopg2

DB_CONFIG = {
    "dbname": "omega_bank",
    "user": "omega",
    "password": "omega_pass",
    "host": "localhost"
}

def expire_authorizations():

    conn = psycopg2.connect(**DB_CONFIG)

    while True:

        try:

            with conn:

                with conn.cursor() as cur:

                    cur.execute("""
                        SELECT
                            id,
                            wallet_id,
                            amount
                        FROM authorization_holds
                        WHERE
                            status='AUTHORIZED'
                        AND
                            expires_at <= NOW()
                        FOR UPDATE SKIP LOCKED
                    """)

                    rows = cur.fetchall()

                    for row in rows:

                        hold_id = row[0]
                        wallet_id = row[1]
                        amount = row[2]

                        cur.execute("""
                            UPDATE authorization_holds
                            SET
                                status='EXPIRED',
                                updated_at=NOW()
                            WHERE id=%s
                        """, (hold_id,))

                        print(
                            f"EXPIRED HOLD :: "
                            f"{hold_id} :: "
                            f"{amount}"
                        )

            time.sleep(5)

        except Exception as e:

            print("EXPIRATION WORKER ERROR")
            print(str(e))

            time.sleep(5)

if __name__ == "__main__":
    expire_authorizations()
