#!/usr/bin/env python3

import sqlite3
import json
import hashlib
import time

DB = "omega_ledger.db"


def hash_event(event):
    return hashlib.sha256(json.dumps(event, sort_keys=True).encode()).hexdigest()


def run():
    print("⚡ OMEGA STRIPE WEBHOOK RECONCILIATION CORE v1")

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # simulate Stripe webhook event (REAL STRUCTURE, SAFE MODE)
    stripe_event = {
        "id": "evt_test_recon_001",
        "type": "payment_intent.succeeded",
        "amount": 13300000000,
        "currency": "usd",
        "account_id": "OMEGA_RESERVE_LEDGER",
        "timestamp": time.time()
    }

    event_hash = hash_event(stripe_event)

    # check idempotency
    cur.execute("""
        SELECT id FROM ledger_events WHERE id = ?
    """, (stripe_event["id"],))

    exists = cur.fetchone()

    if exists:
        print(json.dumps({
            "status": "DUPLICATE_EVENT",
            "event_id": stripe_event["id"]
        }, indent=2))
        conn.close()
        return

    # insert into ledger
    cur.execute("""
        INSERT INTO ledger_events (id, type, payload, timestamp)
        VALUES (?, ?, ?, ?)
    """, (
        stripe_event["id"],
        stripe_event["type"],
        json.dumps(stripe_event),
        str(stripe_event["timestamp"])
    ))

    conn.commit()

    print(json.dumps({
        "status": "STRIPE_EVENT_INGESTED",
        "event_hash": event_hash,
        "amount": stripe_event["amount"]
    }, indent=2))

    conn.close()


if __name__ == "__main__":
    run()
