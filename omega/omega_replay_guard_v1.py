def validate_replay(conn):
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM ledger_events")
    events = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM stripe_event_log")
    logs = cur.fetchone()[0]

    return {
        "ledger_events": events,
        "stripe_events": logs,
        "replay_safe": events >= logs
    }
