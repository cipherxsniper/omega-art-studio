#!/usr/bin/env python3

class ExecutionBlocked(Exception):
    pass


def enforce_invariants(wallet, amount):
    """
    HARD STOP: no exceptions, no soft warnings.
    """

    available = wallet["settled_balance"] - wallet["locked_balance"]

    if amount > available:
        raise ExecutionBlocked(
            f"[INVARIANT BLOCK] insufficient liquidity: {amount} > {available}"
        )


def require_hold(cur, transaction_id):
    cur.execute("""
        SELECT status FROM authorization_holds
        WHERE transaction_id = %s
        FOR UPDATE
    """, (transaction_id,))

    row = cur.fetchone()
    if not row or row[0] != "AUTHORIZED":
        raise ExecutionBlocked("[AUTH MISSING OR INVALID HOLD]")
