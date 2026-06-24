file = "omega_stripe_webhook_revenue_intake_v1.py"

handler = '''

def handle_checkout_session_completed(event, conn):
    session = event["data"]["object"]

    subscription_id = session.get("subscription")
    customer_id = session.get("customer")

    line_items = session.get("line_items", {}).get("data", [])
    price_id = None

    if line_items:
        price_id = line_items[0].get("price", {}).get("id")

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
'''

with open(file, "a") as f:
    f.write(handler)

print("CHECKOUT SESSION HANDLER ADDED")
