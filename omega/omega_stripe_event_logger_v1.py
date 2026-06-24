import json
import time

def log_stripe_event(conn, event):
    """
    Deterministic Stripe event log (billing.db safe)
    """
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS stripe_event_log (
            event_id TEXT PRIMARY KEY,
            event_type TEXT,
            payload TEXT,
            status TEXT,
            created_at TEXT
        )
    """)

    event_id = event.get("id")
    event_type = event.get("type")

    cur.execute("""
        INSERT OR IGNORE INTO stripe_event_log (
            event_id, event_type, payload, status, created_at
        ) VALUES (?, ?, ?, ?, ?)
    """, (
        event_id,
        event_type,
        json.dumps(event),
        "PROCESSED",
        time.time()
    ))

    conn.commit()
    return True
