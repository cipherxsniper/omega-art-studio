#!/usr/bin/env python3

import time
import psycopg2
from contextlib import contextmanager

DB_CONFIG = {
    "dbname": "omega_bank",
    "user": "omega",
    "host": "localhost",
    "port": 5432
}

POLL_INTERVAL = 5

@contextmanager
def db():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()

def fail(cur, invariant, details, severity="CRITICAL"):

    cur.execute("""

        INSERT INTO invariant_failures
        (
            invariant_name,
            failure_details,
            severity
        )

        VALUES
        (
            %s,
            %s,
            %s
        )

    """, (

        invariant,
        details,
        severity

    ))

def verify_double_entry(cur):

    cur.execute("""

        SELECT
            transaction_id,

            SUM(

                CASE

                    WHEN direction='CREDIT'
                    THEN amount

                    ELSE -amount

                END

            ) AS net

        FROM ledger_entries

        GROUP BY transaction_id

        HAVING ABS(

            SUM(

                CASE

                    WHEN direction='CREDIT'
                    THEN amount

                    ELSE -amount

                END

            )

        ) > 0.0001

    """)

    rows = cur.fetchall()

    for row in rows:

        fail(
            cur,
            "DOUBLE_ENTRY_FAILURE",
            f"transaction={row[0]} net={row[1]}"
        )

def verify_wallet_projection(cur):

    cur.execute("""

        WITH ledger_balances AS (

            SELECT

                wallet_id,

                SUM(

                    CASE

                        WHEN direction='CREDIT'
                        THEN amount

                        ELSE -amount

                    END

                ) AS ledger_balance

            FROM ledger_entries

            GROUP BY wallet_id

        )

        SELECT

            w.id,
            w.settled_balance,
            COALESCE(l.ledger_balance, 0)

        FROM wallets w

        LEFT JOIN ledger_balances l
        ON w.id = l.wallet_id

        WHERE ABS(

            w.settled_balance -
            COALESCE(l.ledger_balance, 0)

        ) > 0.0001

    """)

    rows = cur.fetchall()

    for row in rows:

        fail(
            cur,
            "WALLET_PROJECTION_DRIFT",
            f"wallet={row[0]} settled={row[1]} ledger={row[2]}"
        )

def verify_negative_treasury(cur):

    cur.execute("""

        SELECT

            asset_type,
            available_balance,
            locked_balance

        FROM treasury_state

        WHERE
            available_balance < 0
            OR locked_balance < 0

    """)

    rows = cur.fetchall()

    for row in rows:

        fail(
            cur,
            "NEGATIVE_TREASURY",
            f"asset={row[0]}"
        )

def verify_orphan_holds(cur):

    cur.execute("""

        SELECT

            transaction_id,
            wallet_id,
            amount

        FROM authorization_holds

        WHERE
            status='AUTHORIZED'
            AND expires_at < now()

    """)

    rows = cur.fetchall()

    for row in rows:

        fail(
            cur,
            "ORPHAN_AUTH_HOLD",
            f"tx={row[0]} wallet={row[1]}"
        )

def verify_invalid_lifecycle(cur):

    cur.execute("""

        SELECT

            transaction_id,
            status

        FROM authorization_holds

        WHERE status NOT IN (

            'AUTHORIZED',
            'CAPTURED',
            'REVERSED',
            'FAILED',
            'EXPIRED'

        )

    """)

    rows = cur.fetchall()

    for row in rows:

        fail(
            cur,
            "INVALID_LIFECYCLE_STATE",
            f"tx={row[0]} state={row[1]}"
        )

def verify_duplicate_idempotency(cur):

    cur.execute("""

        SELECT

            idempotency_key,
            COUNT(*)

        FROM ledger_entries

        GROUP BY idempotency_key

        HAVING COUNT(*) > 1

    """)

    rows = cur.fetchall()

    for row in rows:

        fail(
            cur,
            "DUPLICATE_IDEMPOTENCY",
            f"key={row[0]} count={row[1]}"
        )

def verify_negative_available(cur):

    cur.execute("""

        SELECT

            wallet_id,
            available_balance

        FROM wallet_state

        WHERE available_balance < 0

    """)

    rows = cur.fetchall()

    for row in rows:

        fail(
            cur,
            "NEGATIVE_AVAILABLE_BALANCE",
            f"wallet={row[0]} balance={row[1]}"
        )

def verify_queue_integrity(cur):

    cur.execute("""

        SELECT COUNT(*)

        FROM settlement_queue

        WHERE
            status='PROCESSING'
            AND updated_at < now() - interval '10 minutes'

    """)

    stuck = cur.fetchone()[0]

    if stuck > 0:

        fail(
            cur,
            "STUCK_SETTLEMENT_JOBS",
            f"count={stuck}"
        )

def run_verification():

    with db() as conn:

        with conn.cursor() as cur:

            verify_double_entry(cur)

            verify_wallet_projection(cur)

            verify_negative_treasury(cur)

            verify_orphan_holds(cur)

            verify_invalid_lifecycle(cur)

            verify_duplicate_idempotency(cur)

            verify_negative_available(cur)

            verify_queue_integrity(cur)

            conn.commit()

def kernel():

    print("[OMEGA] Verification kernel online.")

    while True:

        try:

            run_verification()

            print("[VERIFY] invariants verified")

        except Exception as e:

            print(f"[VERIFY FAILED] {e}")

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    kernel()

