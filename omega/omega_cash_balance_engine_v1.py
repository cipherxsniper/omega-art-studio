def apply_stripe_cashflow(conn, amount_cents):
    """
    Adds Stripe revenue into system treasury view.
    Deterministic ledger-safe update.
    """

    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS cash_balance (
            id TEXT PRIMARY KEY,
            balance REAL
        )
    """)

    cur.execute("""
        INSERT OR IGNORE INTO cash_balance (id, balance)
        VALUES ('STRIPE_TREASURY', 0)
    """)

    amount = float(amount_cents) / 100.0

    cur.execute("""
        UPDATE cash_balance
        SET balance = balance + ?
        WHERE id = 'STRIPE_TREASURY'
    """, (amount,))

    conn.commit()
    return amount
