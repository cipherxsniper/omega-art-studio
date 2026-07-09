from omega_event_bus_core_v1 import connect_db
import time

def upsert_subscription(session, conn):
    try:
        subscription_id = session.get("subscription")
        customer_id = session.get("customer")
        price_id = (
            session.get("metadata", {}).get("price_id")
            or session.get("subscription_details", {}).get("price", {}).get("id")
        )

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
            subscription_id,
            customer_id,
            "active",
            price_id,
            session.get("current_period_start", 0),
            session.get("current_period_end", 0),
            0,
            time.time()
        ))
        conn.commit()

    except Exception as e:
        print("[SUBSCRIPTION INSERT ERROR]", str(e))
