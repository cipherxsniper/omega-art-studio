import uuid
import time
import psycopg2
from decimal import Decimal

DB="omega_bank"
USER="omega"

def conn():
    return psycopg2.connect(
        dbname=DB,
        user=USER
    )

def expire_holds():

    c = conn()

    with c.cursor() as cur:

        cur.execute("""
            SELECT
                id,
                auth_id,
                wallet_id,
                hold_amount
            FROM pending_holds
            WHERE
                status='ACTIVE'
                AND expires_at < NOW()
        """)

        holds = cur.fetchall()

        for hold in holds:

            hold_id = hold[0]
            auth_id = hold[1]
            wallet_id = hold[2]
            amount = Decimal(hold[3])

            cur.execute("""
                UPDATE pending_holds
                SET status='EXPIRED'
                WHERE id=%s
            """, (hold_id,))

            cur.execute("""
                INSERT INTO authorization_expirations (
                    id,
                    auth_id,
                    wallet_id,
                    expired_amount
                )
                VALUES (%s,%s,%s,%s)
            """, (
                str(uuid.uuid4()),
                auth_id,
                wallet_id,
                amount
            ))

    c.commit()
    c.close()

def run():

    print("OMEGA HOLD EXPIRATION WORKER ONLINE")

    while True:

        try:
            expire_holds()
            time.sleep(5)

        except Exception as e:
            print("[HOLD EXPIRATION ERROR]", e)
            time.sleep(5)

if __name__ == "__main__":
    run()

