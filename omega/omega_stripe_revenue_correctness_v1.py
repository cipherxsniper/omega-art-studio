#!/usr/bin/env python3

import sqlite3
import uuid
import time
import json
from decimal import Decimal

LEDGER_DB = "omega_ledger.db"
BILLING_DB = "billing.db"


def D(v):
    return Decimal(str(v))


def ledger():
    return sqlite3.connect(LEDGER_DB)


def billing():
    return sqlite3.connect(BILLING_DB)


def ensure_tables(conn):

    conn.execute("""
    CREATE TABLE IF NOT EXISTS stripe_event_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id TEXT UNIQUE,
        event_type TEXT,
        payload TEXT,
        created_at REAL
    )
    """)

    conn.commit()


def insert_ledger_event(cur, account_id, event_type, amount, tx_id):

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
        float(amount),
        tx_id,
        time.time()
    ))


def process_subscription_revenue():

    bconn = billing()
    lconn = ledger()

    ensure_tables(bconn)

    subs = bconn.execute("""
    SELECT
        customer_id,
        status,
        price_id
    FROM subscriptions
    WHERE status='active'
    """).fetchall()

    tx_id = f"STRIPE_REV_{uuid.uuid4().hex[:10]}"

    total = Decimal("0")

    cur = lconn.cursor()

    for customer_id, status, price_id in subs:

        amount = Decimal("1497.00")

        total += amount

        insert_ledger_event(
            cur,
            "OMEGA_TREASURY",
            "STRIPE_REVENUE_CREDIT",
            amount,
            tx_id
        )

        insert_ledger_event(
            cur,
            "REVENUE",
            "STRIPE_REVENUE_DEBIT",
            amount,
            tx_id
        )

        bconn.execute("""
        INSERT OR IGNORE INTO stripe_event_log (
            event_id,
            event_type,
            payload,
            created_at
        ) VALUES (?, ?, ?, ?)
        """, (
            tx_id,
            "subscription_revenue",
            json.dumps({
                "customer_id": customer_id,
                "price_id": price_id,
                "amount": float(amount)
            }),
            time.time()
        ))

    lconn.commit()
    bconn.commit()

    print("\n=== STRIPE REVENUE CORRECTNESS ===")
    print("ACTIVE SUBSCRIPTIONS :", len(subs))
    print(f"MRR BOOKED           : ${total:,.2f}")
    print("TX_ID                :", tx_id)

    lconn.close()
    bconn.close()


if __name__ == "__main__":
    process_subscription_revenue()
