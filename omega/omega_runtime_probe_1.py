import sqlite3

conn = sqlite3.connect("omega_ledger.db")

print("=== SUBSCRIPTIONS TABLE ===")
rows = conn.execute("SELECT * FROM subscriptions ORDER BY created_at DESC LIMIT 10").fetchall()
print(rows)

print("\n=== EVENTS ===")
events = conn.execute("SELECT id, type, timestamp FROM events ORDER BY timestamp DESC LIMIT 5").fetchall()
print(events)

print("\n=== STRIPE EVENT LOG ===")
stripe = conn.execute("SELECT event_type, status FROM stripe_event_log ORDER BY created_at DESC LIMIT 5").fetchall()
print(stripe)
