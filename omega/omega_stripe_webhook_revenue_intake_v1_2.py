def process_stripe_event(payload):
    conn = connect_db()
    cur = conn.cursor()

    try:
        event = build_stripe_event(payload)

        # STRIPE EVENT ROUTER (minimal safe hook)
        if event.get("type") == "payment_intent.succeeded":
            create_subscription(event)

        result = insert_event(cur, event)

        conn.commit()
        return result

    except Exception as e:
        print('[SUBSCRIPTION INSERT ERROR]', str(e))
        conn.rollback()
        return None

    finally:
        conn.close()

from omega_stripe_identity_binding_v1 

import normalize_subscription_payload

data = normalize_subscription_payload(session, event)

conn.execute("""
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
    data["subscription_id"],
    data["customer_id"],
    data["status"],
    data["price_id"],
    data["current_period_start"],
    data["current_period_end"],
    data["cancel_at_period_end"],
    data["created_at"]
))
