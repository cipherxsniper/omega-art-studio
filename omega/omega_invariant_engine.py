#!/usr/bin/env python3

# =========================================================
# OMEGA INVARIANT ENGINE
# Deterministic Financial Integrity Layer
# =========================================================

import time
import uuid
import psycopg2
from contextlib import contextmanager

# =========================================================
# DATABASE CONFIG
# =========================================================

DB_CONFIG = {
    "dbname": "omega_bank",
    "user": "omega",
    "host": "localhost",
    "port": 5432
}

# =========================================================
# DATABASE CONTEXT
# =========================================================

@contextmanager
def db():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()

# =========================================================
# FAILURE RECORDER
# =========================================================

def record_failure(name, details, severity="CRITICAL"):

    with db() as conn:
        with conn.cursor() as cur:

            cur.execute("""

                INSERT INTO invariant_failures
                (
                    id,
                    invariant_name,
                    failure_details,
                    severity
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s
                )

            """, (

                str(uuid.uuid4()),
                name,
                details,
                severity

            ))

        conn.commit()

# =========================================================
# INVARIANT:
# DOUBLE ENTRY MUST BALANCE
# =========================================================

def check_double_entry():

    with db() as conn:
        with conn.cursor() as cur:

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

            if rows:

                for tx_id, net in rows:

                    record_failure(
                        "DOUBLE_ENTRY_IMBALANCE",
                        f"transaction={tx_id} net={net}"
                    )

                return False

    return True

# =========================================================
# INVARIANT:
# NO NEGATIVE LOCKED BALANCES
# =========================================================

def check_locked_balances():

    with db() as conn:
        with conn.cursor() as cur:

            cur.execute("""

                SELECT
                    id,
                    locked_balance

                FROM wallets

                WHERE locked_balance < 0

            """)

            rows = cur.fetchall()

            if rows:

                for wallet_id, locked in rows:

                    record_failure(
                        "NEGATIVE_LOCKED_BALANCE",
                        f"wallet={wallet_id} locked={locked}"
                    )

                return False

    return True

# =========================================================
# INVARIANT:
# AVAILABLE BALANCE CONSISTENCY
# =========================================================

def check_wallet_projection():

    with db() as conn:
        with conn.cursor() as cur:

            cur.execute("""

                SELECT
                    id,
                    settled_balance,
                    locked_balance,
                    available_balance

                FROM wallets

            """)

            rows = cur.fetchall()

            for row in rows:

                wallet_id = row[0]
                settled = float(row[1])
                locked = float(row[2])
                available = float(row[3])

                expected = settled - locked

                if round(expected, 2) != round(available, 2):

                    record_failure(
                        "PROJECTION_MISMATCH",
                        f"wallet={wallet_id} expected={expected} actual={available}"
                    )

                    return False

    return True

# =========================================================
# INVARIANT:
# EXPIRED AUTH HOLDS
# =========================================================

def check_expired_holds():

    with db() as conn:
        with conn.cursor() as cur:

            cur.execute("""

                SELECT
                    transaction_id,
                    wallet_id,
                    amount

                FROM authorization_holds

                WHERE status='AUTHORIZED'
                AND expires_at < now()

            """)

            rows = cur.fetchall()

            if rows:

                for tx_id, wallet_id, amount in rows:

                    record_failure(
                        "EXPIRED_AUTH_HOLD",
                        f"tx={tx_id} wallet={wallet_id} amount={amount}",
                        "HIGH"
                    )

                return False

    return True

# =========================================================
# INVARIANT:
# TREASURY CONSISTENCY
# =========================================================

def check_treasury():

    with db() as conn:
        with conn.cursor() as cur:

            cur.execute("""

                SELECT
                    available_balance,
                    locked_balance,
                    pending_outflow

                FROM treasury_state

                WHERE asset_type='USD'

            """)

            treasury = cur.fetchone()

            if treasury is None:

                record_failure(
                    "TREASURY_STATE_MISSING",
                    "USD treasury state missing"
                )

                return False

            available = float(treasury[0])
            locked = float(treasury[1])
            pending = float(treasury[2])

            total = available - locked - pending

            if total < 0:

                record_failure(
                    "TREASURY_NEGATIVE",
                    f"effective_balance={total}"
                )

                return False

    return True

# =========================================================
# INVARIANT:
# DUPLICATE IDEMPOTENCY
# =========================================================

def check_idempotency():

    with db() as conn:
        with conn.cursor() as cur:

            cur.execute("""

                SELECT
                    idempotency_key,
                    COUNT(*)

                FROM ledger_entries

                GROUP BY idempotency_key

                HAVING COUNT(*) > 1

            """)

            rows = cur.fetchall()

            if rows:

                for key, count in rows:

                    record_failure(
                        "DUPLICATE_IDEMPOTENCY",
                        f"key={key} count={count}"
                    )

                return False

    return True

# =========================================================
# MASTER CHECK LOOP
# =========================================================

def run_checks():

    checks = [

        check_double_entry,
        check_locked_balances,
        check_wallet_projection,
        check_expired_holds,
        check_treasury,
        check_idempotency

    ]

    for check in checks:

        try:

            ok = check()

            if ok:
                print(f"[PASS] {check.__name__}")

            else:
                print(f"[FAIL] {check.__name__}")

        except Exception as e:

            record_failure(
                "ENGINE_EXCEPTION",
                str(e),
                "CRITICAL"
            )

            print(f"[ERROR] {check.__name__}: {e}")

# =========================================================
# MAIN LOOP
# =========================================================

if __name__ == "__main__":

    print("[OMEGA] Invariant Engine Started")

    while True:

        run_checks()

        time.sleep(10)

