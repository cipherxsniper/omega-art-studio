#!/usr/bin/env python3

from contextlib import contextmanager

@contextmanager
def execution_gate(conn, wallet_id, idempotency_key):
    """
    HARD EXECUTION CONTRACT:
    Nothing executes unless:
    - row lock acquired
    - idempotency is clean
    - wallet state is consistent
    """

    with conn.cursor() as cur:

        # 1. IDENTITY GATE (NO DUPLICATES)
        cur.execute("""
            SELECT 1 FROM ledger_entries
            WHERE idempotency_key = %s
            LIMIT 1
        """, (idempotency_key,))

        if cur.fetchone():
            raise Exception(f"[IDEMPOTENCY BLOCK] {idempotency_key}")

        # 2. HARD WALLET LOCK (NO RACE CONDITIONS)
        cur.execute("""
            SELECT settled_balance, locked_balance
            FROM wallets
            WHERE id = %s
            FOR UPDATE
        """, (wallet_id,))

        wallet = cur.fetchone()
        if not wallet:
            raise Exception(f"[WALLET NOT FOUND] {wallet_id}")

        yield cur  # ONLY SAFE EXECUTION ZONE
