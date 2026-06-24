"""
OMEGA DB ALIGNMENT FIX
Forces Stripe + subscriptions + reconciliation to use billing.db

NO ARCHITECTURE CHANGE — ONLY FIXES WRONG CONNECTION TARGETS
"""

from omega_event_bus_core_v1 import connect_db as legacy_connect_db
import sqlite3
import os

BILLING_DB = "billing.db"

def connect_billing_db():
    conn = sqlite3.connect(BILLING_DB)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def get_stripe_db():
    # ALWAYS use billing.db for Stripe domain
    return connect_billing_db()


def bootstrap_tables():
    conn = connect_billing_db()
    cur = conn.cursor()

    # subscriptions (safe create if missing)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subscription_id TEXT,
        customer_id TEXT,
        status TEXT,
        price_id TEXT,
        current_period_start INTEGER,
        current_period_end INTEGER,
        cancel_at_period_end INTEGER,
        created_at TEXT
    )
    """)

    # stripe event log (missing in your system)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS stripe_event_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id TEXT UNIQUE,
        event_type TEXT,
        payload TEXT,
        status TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    bootstrap_tables()
    print("[OMEGA DB ALIGNMENT] billing.db is now canonical for Stripe + subscriptions")
