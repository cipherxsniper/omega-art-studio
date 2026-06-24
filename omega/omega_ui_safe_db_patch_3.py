import psycopg2

def safe_query(conn, query, params=None):
    """
    Safe DB wrapper:
    - prevents aborted transaction poisoning
    - auto rollback on failure
    """
    try:
        cur = conn.cursor()
        cur.execute(query, params or ())
        result = cur.fetchall() if cur.description else None
        conn.commit()
        return result

    except Exception as e:
        # CRITICAL: clear aborted transaction state
        conn.rollback()
        return None
