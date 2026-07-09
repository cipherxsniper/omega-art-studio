#!/usr/bin/env python3

from omega_event_bus_core_v1 import connect_db

def get_billing_conn():
    conn = connect_db()
    conn.execute("ATTACH DATABASE 'billing.db' AS billing")
    return conn

def run_alignment_check():
    conn = get_billing_conn()

    print("=== BILLING SUBSCRIPTIONS ===")
    rows = conn.execute("""
        SELECT * FROM billing.subscriptions ORDER BY created_at DESC LIMIT 10
    """).fetchall()

    print(rows)

    print("\n=== STRIPE EVENT LOG ===")
    logs = conn.execute("""
        SELECT * FROM billing.stripe_event_log ORDER BY created_at DESC LIMIT 10
    """).fetchall()

    print(logs)

if __name__ == "__main__":
    run_alignment_check()
