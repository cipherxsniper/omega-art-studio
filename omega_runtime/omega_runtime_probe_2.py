#!/usr/bin/env python3
import sqlite3
from omega_db_registry import get_db

conn = sqlite3.connect(get_db("ledger"))

print("=== SUBSCRIPTIONS TABLE ===")
rows = conn.execute("SELECT * FROM subscriptions ORDER BY created_at DESC LIMIT 10").fetchall()
print(rows)

print("\n=== EVENTS ===")
events = conn.execute("SELECT * FROM events ORDER BY timestamp DESC LIMIT 5").fetchall()
print(events)
