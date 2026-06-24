if event.get("type") == "checkout.session.completed":
    session = event["data"]["object"]

    subscription_id = session.get("subscription")
    customer_id = session.get("customer")
    price_id = session.get("display_items", [{}])[0].get("price", {}).get("id")

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
