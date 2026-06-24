#!/usr/bin/env python3

def precommit_validate(conn, wallet_id, delta):
    with conn.cursor() as cur:

        cur.execute("""
            SELECT settled_balance
            FROM wallets
            WHERE id=%s
            FOR UPDATE
        """, (wallet_id,))

        wallet_balance = float(cur.fetchone()[0])

        cur.execute("""
            SELECT COALESCE(SUM(
                CASE WHEN direction='CREDIT' THEN amount
                ELSE -amount END
            ),0)
            FROM ledger_entries
            WHERE wallet_id=%s
        """, (wallet_id,))

        ledger_balance = float(cur.fetchone()[0])

        projected = ledger_balance + delta

        # HARD INVARIANT
        if projected != wallet_balance:
            raise Exception(
                f"[INVARIANT BLOCKED] wallet={wallet_id} "
                f"ledger={ledger_balance} delta={delta} projected={projected} wallet={wallet_balance}"
            )

        return True
