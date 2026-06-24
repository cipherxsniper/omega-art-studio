import sqlite3

conn = sqlite3.connect("event_queue.db")

conn.execute("""
CREATE TABLE IF NOT EXISTS queue (
    id TEXT PRIMARY KEY,
    type TEXT,
    payload TEXT,
    status TEXT,
    created_at REAL DEFAULT (strftime('%s','now'))
)
""")

conn.commit()
print("Queue initialized")
