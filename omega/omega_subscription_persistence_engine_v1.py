import json
import time

def persist_subscription_state(conn, event):
    """
    Deterministic subscription persistence layer.
    Source of truth: billing.db only.
    """

    session = event["data"]["object"]

    stripe_event_id = event.get("id")
    subscription_id = session.get("subscription")
    customer_id = session.get("customer")
    price_id = session.get("metadata", {}).get("price_id", "UNKNOWN")

    created_at = session.get("created", time.time())

    cur = conn.cursor()

    # IDEMPOTENCY (event-level)
    cur.execute("""
        SELECT 1 FROM stripe_event_log WHERE event_id = ?
    """, (stripe_event_id,))

    if cur.fetchone():
        return

    # log event first (replay safe)
    cur.execute("""
        INSERT OR IGNORE INTO stripe_event_log (
            event_id, event_type, payload, created_at
        ) VALUES (?, ?, ?, ?)
    """, (
        stripe_event_id,
        event.get("type", "checkout.session.completed"),
        json.dumps(event),
        time.time()
    ))

    # deterministic upsert subscription
    cur.execute("""
        INSERT OR REPLACE INTO subscriptions (
            id,
            customer_id,
            status,
            price_id,
            created_at
        ) VALUES (
            COALESCE((SELECT id FROM subscriptions WHERE customer_id=?), NULL),
            ?,
            ?,
            ?,
            ?
        )
    """, (
        customer_id,
        customer_id,
        "active",
        price_id,
        created_at
    ))

    conn.commit()
