from models.subscriptions import subscriptions


def has_access(user_id):
    cur = subscriptions.conn.cursor()
    cur.execute("""
        SELECT status FROM subscriptions WHERE user_id=?
    """, (user_id,))

    row = cur.fetchone()

    return row is not None and row[0] == "active"
