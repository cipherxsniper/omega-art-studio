"""
OMEGA INVARIANT EXECUTION GATE
Hard stop system if financial correctness breaks
"""

def check_invariants(conn):
    with conn.cursor() as cur:

        # 1. Wallet vs ledger must match
        cur.execute("""
            SELECT w.id,
                   w.settled_balance,
                   COALESCE(SUM(
                        CASE WHEN le.direction='CREDIT' THEN le.amount
                        ELSE -le.amount END
                   ),0) as ledger_balance
            FROM wallets w
            LEFT JOIN ledger_entries le ON w.id = le.wallet_id
            GROUP BY w.id, w.settled_balance
        """)

        mismatches = []

        for wallet_id, wallet_balance, ledger_balance in cur.fetchall():
            if float(wallet_balance) != float(ledger_balance):
                mismatches.append({
                    "wallet": wallet_id,
                    "wallet_balance": wallet_balance,
                    "ledger_balance": ledger_balance
                })

        # HARD FAIL MODE (not logging)
        if mismatches:
            raise Exception(f"INVARIANT VIOLATION: {mismatches}")

        return True
