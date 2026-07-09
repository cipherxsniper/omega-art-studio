def get_events(cur):
    cur.execute("PRAGMA table_info(events)")
    cols = [c[1] for c in cur.fetchall()]

    event_id_col = "event_id" if "event_id" in cols else cols[0]
    type_col = "type" if "type" in cols else "event_type"
    payload_col = "payload" if "payload" in cols else "event_data"
    hash_col = "hash" if "hash" in cols else "event_hash"

    query = f"""
        SELECT {event_id_col}, {type_col}, {payload_col}, {hash_col}
        FROM events
        ORDER BY rowid ASC
    """

    cur.execute(query)
    return cur.fetchall()
