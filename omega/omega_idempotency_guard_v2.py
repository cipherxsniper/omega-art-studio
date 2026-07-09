def is_settled(cur, event_id: str) -> bool:
    cur.execute("""
        SELECT 1
        FROM omega_idempotency_log
        WHERE event_id = %s
        LIMIT 1
    """, (event_id,))

    return cur.fetchone() is not None
