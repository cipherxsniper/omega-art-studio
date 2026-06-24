import time

def settle(conn, account_id, event_type, amount, tx_id):

    cur = conn.cursor()

    cur.execute("""
        SELECT 1 FROM ledger_events
        WHERE tx_id = ?
    """, (tx_id,))

    if cur.fetchone():
        return

    cur.execute("""
        INSERT INTO ledger_events (
            account_id,
            event_type,
            amount,
            tx_id,
            timestamp
        ) VALUES (?, ?, ?, ?, ?)
    """, (
        account_id,
        event_type,
        amount,
        tx_id,
        time.time()
    ))

    conn.commit()
