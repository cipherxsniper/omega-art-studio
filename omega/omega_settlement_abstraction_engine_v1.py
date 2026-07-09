import time

def settle(conn, account_from, account_to, amount, tx_id):
    """
    SINGLE SOURCE OF TRUTH FOR ALL MONEY MOVEMENT.
    """

    cur = conn.cursor()

    # debit
    cur.execute("""
        INSERT INTO ledger_events (
            account_id, event_type, amount, tx_id, timestamp
        ) VALUES (?, ?, ?, ?, ?)
    """, (
        account_from,
        "DEBIT",
        amount,
        tx_id,
        time.time()
    ))

    # credit
    cur.execute("""
        INSERT INTO ledger_events (
            account_id, event_type, amount, tx_id, timestamp
        ) VALUES (?, ?, ?, ?, ?)
    """, (
        account_to,
        "CREDIT",
        amount,
        tx_id,
        time.time()
    ))

    conn.commit()
