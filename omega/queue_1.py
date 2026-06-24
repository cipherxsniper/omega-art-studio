import sqlite3
import uuid
import json
import time

DB = "event_queue.db"


def push_event(event_type, payload):
    conn = sqlite3.connect(DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS queue (
            id TEXT PRIMARY KEY,
            type TEXT,
            payload TEXT,
            status TEXT,
            created_at REAL
        )
    """)

    conn.execute(
        "INSERT INTO queue VALUES (?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()),
            event_type,
            json.dumps(payload),
            "pending",
            time.time()
        )
    )

    conn.commit()
    conn.close()
