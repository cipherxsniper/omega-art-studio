import json
import time

def is_duplicate(cur, event_id):

    cur.execute("""
        SELECT 1 FROM stripe_event_log
        WHERE event_id = ?
    """, (event_id,))

    return cur.fetchone() is not None


def log_event(cur, event):

    cur.execute("""
        INSERT OR IGNORE INTO stripe_event_log (
            event_id,
            event_type,
            payload,
            created_at
        ) VALUES (?, ?, ?, ?)
    """, (
        event["id"],
        event.get("type"),
        json.dumps(event),
        time.time()
    ))
