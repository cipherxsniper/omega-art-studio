"""
=========================================================
OMEGA AI — GITHUB CHECKPOINT FIX
Subscription Insert Fix (PaymentIntent Path)
Developed by Thomas Lee Harvey
=========================================================

FIX:
- Handles payment_intent.succeeded correctly
- Inserts into subscriptions table
- Uses metadata price_id (Stripe Payment Links safe)
"""

import time

def handle_payment_intent_succeeded(event, conn):
    obj = event["data"]["object"]
    print('[DEBUG SUBSCRIPTION]', obj)

    # --- CORE EXTRACTION ---
    customer_id = obj.get("customer")
    amount = obj.get("amount")
    currency = obj.get("currency")
    status = obj.get("status")

    metadata = obj.get("metadata", {})

    price_id = (
        metadata.get("price_id")
        or metadata.get("price")
        or "price_unknown"
    )

    subscription_id = obj.get("id")

    now = time.time()

    # --- INSERT SUBSCRIPTION STATE ---
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
        now,
        now + 30*24*60*60,  # default 30-day window for Payment Link model
        0,
        now
    ))

    conn.commit()

    print("[OMEGA] Subscription inserted:", subscription_id)
