#!/usr/bin/env python3

import sqlite3
import hashlib
import time
from datetime import datetime, timezone


LEDGER_DB = "omega_ledger.db"
BILLING_DB = "billing.db"


def make_tx_id(customer_id, subscription_id, price_id):
    raw = f"{customer_id}:{subscription_id}:{price_id}"
    return "SYNC_" + hashlib.sha256(raw.encode()).hexdigest()[:24]


def already_exists(conn, tx_id):
    cur = conn.cursor()
    cur.execute("""
        SELECT 1 FROM ledger_events WHERE tx_id = ?
    """, (tx_id,))
    return cur.fetchone() is not None


def insert_ledger_event(conn, account_id, event_type, amount, tx_id):
    cur = conn.cursor()

    timestamp = datetime.now(timezone.utc).timestamp()

    cur.execute("""
        INSERT INTO ledger_events (
            account_id,
            event_type,
            amount,
            tx_id,
            timestamp
        ) VALUES (?, ?, ?, ?, ?)
    """, (
        account_id,
        event_type,
        amount,
        tx_id,
        timestamp
    ))


def sync():
    ledger = sqlite3.connect(LEDGER_DB)
    billing = sqlite3.connect(BILLING_DB)

    billing.row_factory = sqlite3.Row

    cur = billing.cursor()

    cur.execute("""
        SELECT *
        FROM subscriptions
        WHERE status = 'active'
    """)

    rows = cur.fetchall()

    synced = 0
    skipped = 0

    for sub in rows:
        customer_id = sub["customer_id"]
        subscription_id = sub["subscription_id"] or "NULL_SUB"
        price_id = sub["price_id"]

        tx_id = make_tx_id(customer_id, subscription_id, price_id)

        if already_exists(ledger, tx_id):
            skipped += 1
            continue

        # ─────────────────────────────────────────────
        # OMEGA REVENUE BOOKING LOGIC
        # (Stripe subscription → ledger revenue event)
        # ─────────────────────────────────────────────

        amount = 1497.00  # your SaaS price anchor

        insert_ledger_event(
            ledger,
            account_id="REVENUE",
            event_type="CREDIT_SUBSCRIPTION",
            amount=amount,
            tx_id=tx_id
        )

        # mirror into treasury (optional real accounting layer)
        insert_ledger_event(
            ledger,
            account_id="OMEGA_TREASURY",
            event_type="CREDIT_SUBSCRIPTION",
            amount=amount,
            tx_id=tx_id + "_T"
        )

        ledger.commit()
        synced += 1

    ledger.close()
    billing.close()

    print("\n=== OMEGA BILLING → LEDGER SYNC ===")
    print("ACTIVE SUBSCRIPTIONS:", len(rows))
    print("SYNCED:", synced)
    print("SKIPPED (idempotent):", skipped)
    print("STATUS: COMPLETE\n")


if __name__ == "__main__":
    sync()
