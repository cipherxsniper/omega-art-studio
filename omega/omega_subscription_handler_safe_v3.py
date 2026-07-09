import json
import time

def handle_checkout_session_completed(event, conn):
    try:
        session = event["data"]["object"]

        stripe_event_id = event.get("id")
        subscription_id = session.get("subscription")
        customer_id = session.get("customer")

        price_id = (
            session.get("metadata", {}).get("price_id")
            or session.get("subscription_details", {}).get("price", {}).get("id")
        )

        created_at = session.get("created", time.time())

        cur = conn.cursor()

        # -------------------------
        # IDEMPOTENCY CHECK
        # -------------------------
        cur.execute("""
            SELECT 1 FROM stripe_event_log
            WHERE event_id = ?
        """, (stripe_event_id,))

        if cur.fetchone():
            print("[SKIP] duplicate event:", stripe_event_id)
            return

        # -------------------------
        # EVENT LOG FIRST (REPLAY SAFE)
        # -------------------------
        cur.execute("""
            INSERT INTO stripe_event_log (
                event_id,
                event_type,
                payload,
                status,
                created_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            stripe_event_id,
            "checkout.session.completed",
            json.dumps(event),
            "PROCESSED",
            time.time()
        ))

        # -------------------------
        # SUBSCRIPTION UPSERT
        # -------------------------
        cur.execute("""
            INSERT OR REPLACE INTO subscriptions (
                subscription_id,
                customer_id,
                status,
                price_id,
                current_period_start,
                current_period_end,
                cancel_at_period_end,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            subscription_id,
            customer_id,
            "active",
            price_id,
            session.get("current_period_start", 0),
            session.get("current_period_end", 0),
            0,
            created_at
        ))

        conn.commit()
        print("[OK] subscription committed:", subscription_id)

    except Exception as e:
        conn.rollback()
        print("[FATAL SUBSCRIPTION ERROR]", str(e))
