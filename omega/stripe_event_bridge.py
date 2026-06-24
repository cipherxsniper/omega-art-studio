import sqlite3
import time


def _ensure_ledger():
    conn = sqlite3.connect("omega_ledger.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ledger (
            tx_id TEXT PRIMARY KEY,
            event_type TEXT,
            amount REAL,
            meta TEXT,
            created_at REAL
        )
    """)
    conn.commit()
    conn.close()


def _ensure_subscriptions():
    conn = sqlite3.connect("billing.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stripe_subscription TEXT,
            stripe_customer_id TEXT,
            status TEXT,
            price_id TEXT,
            updated_at REAL
        )
    """)
    conn.commit()
    conn.close()


def write_ledger(tx_id, event_type, amount=0.0, meta="{}"):
    _ensure_ledger()

    conn = sqlite3.connect("omega_ledger.db")
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO ledger
        (tx_id, event_type, amount, meta, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        tx_id,
        event_type,
        amount,
        meta,
        time.time()
    ))

    conn.commit()
    conn.close()


def upsert_subscription(customer_id, subscription_id, status, price_id):
    _ensure_subscriptions()

    conn = sqlite3.connect("billing.db")
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO subscriptions
        (stripe_subscription, stripe_customer_id, status, price_id, updated_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        subscription_id,
        customer_id,
        status,
        price_id,
        time.time()
    ))

    conn.commit()
    conn.close()


def handle_stripe_event(event):
    event_type = event.get("type", "")
    obj = event.get("data", {}).get("object", {})

    # PAYMENT SUCCESS → LEDGER
    if event_type == "payment_intent.succeeded":
        tx_id = obj.get("id", "unknown_tx")
        amount = (obj.get("amount_received") or 0) / 100.0

        write_ledger(
            tx_id=tx_id,
            event_type="PAYMENT_SUCCESS",
            amount=amount,
            meta=str(obj)
        )
        return "ledger_written"

    # SUBSCRIPTION CREATED
    if event_type == "customer.subscription.created":
        price_id = None
        try:
            price_id = obj["items"]["data"][0]["price"]["id"]
        except Exception:
            pass

        upsert_subscription(
            customer_id=obj.get("customer"),
            subscription_id=obj.get("id"),
            status=obj.get("status"),
            price_id=price_id
        )
        return "subscription_created"

    # SUBSCRIPTION UPDATED
    if event_type == "customer.subscription.updated":
        price_id = None
        try:
            price_id = obj["items"]["data"][0]["price"]["id"]
        except Exception:
            pass

        upsert_subscription(
            customer_id=obj.get("customer"),
            subscription_id=obj.get("id"),
            status=obj.get("status"),
            price_id=price_id
        )
        return "subscription_updated"

    return "ignored"
