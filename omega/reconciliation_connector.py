#!/usr/bin/env python3

import psycopg2
from decimal import Decimal

DB_NAME = "omega_bank"
DB_USER = "omega"

def get_db():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER
    )

def reconcile():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            COUNT(*)
        FROM ledger_events
    """)

    total_events = cur.fetchone()[0]

    cur.execute("""
        SELECT
            event_type,
            COUNT(*)
        FROM ledger_events
        GROUP BY event_type
        ORDER BY COUNT(*) DESC
    """)

    grouped = cur.fetchall()

    print("\n=== OMEGA RECONCILIATION REPORT ===")
    print(f"TOTAL EVENTS: {total_events}")
    print("")

    for row in grouped:
        print(f"{row[0]} -> {row[1]}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    reconcile()

