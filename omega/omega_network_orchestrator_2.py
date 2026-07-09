import uuid
import json
import time
import psycopg2
from decimal import Decimal
from datetime import datetime, timedelta

DB="omega_bank"
USER="omega"

def conn():
    return psycopg2.connect(dbname=DB, user=USER)

def enqueue_event(event_type, payload):
    c = conn()

    with c.cursor() as cur:
        cur.execute("""
            INSERT INTO issuer_queue (
                id,
                event_type,
                payload,
                status
            )
            VALUES (%s,%s,%s,%s)
        """, (
            str(uuid.uuid4()),
            event_type,
            json.dumps(payload),
            "PENDING"
        ))

    c.commit()
    c.close()

def create_pending_hold(auth_id, wallet_id, amount):
    c = conn()

    with c.cursor() as cur:
        cur.execute("""
            INSERT INTO pending_holds (
                id,
                auth_id,
                wallet_id,
                hold_amount,
                expires_at,
                status
            )
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            str(uuid.uuid4()),
            auth_id,
            wallet_id,
            amount,
            datetime.utcnow() + timedelta(hours=24),
            "ACTIVE"
        ))

    c.commit()
    c.close()

def compute_interchange(network, amount):
    rates = {
        "VISA": Decimal("0.021"),
        "MASTERCARD": Decimal("0.024"),
        "ACH": Decimal("0.008")
    }

    pct = rates.get(network, Decimal("0.02"))
    return round(Decimal(amount) * pct, 2)

def record_interchange(auth_id, network, amount):
    fee = compute_interchange(network, amount)

    c = conn()

    with c.cursor() as cur:
        cur.execute("""
            INSERT INTO interchange_fee_events (
                id,
                auth_id,
                network,
                fee_amount,
                fee_percent
            )
            VALUES (%s,%s,%s,%s,%s)
        """, (
            str(uuid.uuid4()),
            auth_id,
            network,
            fee,
            float(fee / Decimal(amount))
        ))

    c.commit()
    c.close()

def velocity_check(wallet_id, amount):
    c = conn()

    blocked = False

    with c.cursor() as cur:
        cur.execute("""
            SELECT
                tx_count_1m,
                tx_volume_1m
            FROM fraud_velocity_state
            WHERE wallet_id=%s
        """, (wallet_id,))

        row = cur.fetchone()

        if row:
            tx_count, tx_volume = row

            tx_count += 1
            tx_volume += float(amount)

            risk = min(100, (tx_count * 3) + (tx_volume / 1000))

            if risk > 85:
                blocked = True

            cur.execute("""
                UPDATE fraud_velocity_state
                SET
                    tx_count_1m=%s,
                    tx_volume_1m=%s,
                    risk_score=%s,
                    blocked=%s,
                    updated_at=NOW()
                WHERE wallet_id=%s
            """, (
                tx_count,
                tx_volume,
                risk,
                blocked,
                wallet_id
            ))

        else:
            cur.execute("""
                INSERT INTO fraud_velocity_state (
                    wallet_id,
                    tx_count_1m,
                    tx_volume_1m,
                    risk_score,
                    blocked
                )
                VALUES (%s,%s,%s,%s,%s)
            """, (
                wallet_id,
                1,
                float(amount),
                5,
                False
            ))

    c.commit()
    c.close()

    return blocked

def expire_holds():
    c = conn()

    with c.cursor() as cur:
        cur.execute("""
            UPDATE pending_holds
            SET status='EXPIRED'
            WHERE
                expires_at < NOW()
                AND status='ACTIVE'
        """)

    c.commit()
    c.close()

def process_queue():
    c = conn()

    with c.cursor() as cur:
        cur.execute("""
            SELECT
                id,
                event_type,
                payload
            FROM issuer_queue
            WHERE status='PENDING'
            ORDER BY created_at ASC
            LIMIT 25
        """)

        rows = cur.fetchall()

        for qid, event_type, payload in rows:
            cur.execute("""
                UPDATE issuer_queue
                SET status='PROCESSED'
                WHERE id=%s
            """, (qid,))

    c.commit()
    c.close()

def run():
    print("OMEGA NETWORK ORCHESTRATOR ONLINE")

    while True:
        try:
            expire_holds()
            process_queue()
            time.sleep(2)

        except Exception as e:
            print("[ORCHESTRATOR ERROR]", e)
            time.sleep(2)

if __name__ == "__main__":
    run()

