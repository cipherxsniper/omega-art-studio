def verify_system_integrity(conn):
    """
    Omega Integrity Gate:
    Detects drift between ledger truth and wallet projection.
    """

    with conn.cursor() as cur:

        # STEP 1: Compute ledger-derived truth
        cur.execute("""
            SELECT
                w.id,
                w.settled_balance,
                COALESCE(SUM(
                    CASE
                        WHEN le.direction = 'CREDIT' THEN le.amount
                        ELSE -le.amount
                    END
                ), 0) AS ledger_balance
            FROM wallets w
            LEFT JOIN ledger_entries le
                ON w.id = le.wallet_id
            GROUP BY w.id, w.settled_balance
        """)

        rows = cur.fetchall()

        mismatches = []

        # STEP 2: Strict comparison (no tolerance drift allowed)
        for wallet_id, wallet_balance, ledger_balance in rows:

            wallet_balance = float(wallet_balance or 0)
            ledger_balance = float(ledger_balance or 0)

            if wallet_balance != ledger_balance:
                mismatches.append({
                    "wallet_id": wallet_id,
                    "wallet_balance": wallet_balance,
                    "ledger_balance": ledger_balance,
                    "drift": wallet_balance - ledger_balance
                })

        return mismatches
