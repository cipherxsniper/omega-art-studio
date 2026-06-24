"""
ALL DERIVED SYSTEMS MUST READ FROM ledger_events ONLY
"""

def get_balance(conn, account_id):
    cur = conn.cursor()

    cur.execute("""
        SELECT SUM(
            CASE
                WHEN event_type = 'CREDIT' THEN amount
                WHEN event_type = 'DEBIT' THEN -amount
                ELSE 0
            END
        )
        FROM ledger_events
        WHERE account_id = ?
    """, (account_id,))

    val = cur.fetchone()[0]
    return val or 0.0
