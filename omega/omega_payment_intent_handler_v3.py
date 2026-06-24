import json
import time

def handle_payment_intent_succeeded(event, conn):
    try:
        obj = event["data"]["object"]

        event_id = event.get("id")
        amount = obj.get("amount", 0) / 100.0
        currency = obj.get("currency", "usd")

        customer_id = obj.get("customer")

        metadata = obj.get("metadata", {})
        price_id = metadata.get("price_id")

        cur = conn.cursor()

        # idempotency
        cur.execute("""
            SELECT 1 FROM stripe_event_log WHERE event_id = ?
        """, (event_id,))

        if cur.fetchone():
            print("[SKIP] duplicate payment intent:", event_id)
            return

        # log event
        cur.execute("""
            INSERT INTO stripe_event_log (
                event_id,
                event_type,
                payload,
                status,
                created_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            event_id,
            "payment_intent.succeeded",
            json.dumps(event),
            "PROCESSED",
            time.time()
        ))

        # subscription binding (if exists)
        if price_id:
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
                event_id,
                customer_id,
                "active",
                price_id,
                time.time(),
                time.time(),
                0,
                time.time()
            ))

        conn.commit()
        print("[OK] payment processed:", event_id, amount)

    except Exception as e:
        conn.rollback()
        print("[ERROR payment_intent]", str(e))
