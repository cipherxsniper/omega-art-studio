#!/usr/bin/env python3

from omega_event_bus_core_v1 import connect_db

def connect_runtime():
    conn = connect_db()
    conn.execute("ATTACH DATABASE 'billing.db' AS billing")
    return conn

if __name__ == "__main__":
    conn = connect_runtime()

    print("=== SUBSCRIPTIONS ===")
    print(conn.execute("SELECT * FROM billing.subscriptions").fetchall())
