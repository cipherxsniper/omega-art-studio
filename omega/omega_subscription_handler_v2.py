import json
import time

from omega_cash_balance_engine_v1 import apply_stripe_cashflow
from omega_stripe_event_logger_v1 import log_stripe_event


def handle_checkout_session_completed(event, conn):
    try:
        session = event["data"]["object"]

        event_id = event.get("id")
        subscription_id = session.get("subscription")
        customer_id = session.get("customer")

        price_id = (
            session.get("metadata", {}).get("price_id")
            or session.get("subscription_details", {}).get("price", {}).get("id")
        )

        amount_total = session.get("amount_total", 0)

        cur = conn.cursor()

        # -------------------------
        # IDEMPOTENCY GUARD
        # -------------------------
        cur.execute("""
            SELECT 1 FROM subscriptions WHERE subscription_id = ?
        """, (subscription_id,))

        if cur.fetchone():
            print("[SUBSCRIPTION SKIP] already exists:", subscription_id)
            return

        # -------------------------
        # EVENT LOG (SAFE)
        # -------------------------
        log_stripe_event(conn, event)

        # -------------------------
        # CASH FLOW UPDATE
        # -------------------------
        apply_stripe_cashflow(conn, amount_total)

        # -------------------------
        # SUBSCRIPTION INSERT (DETERMINISTIC)
        # -------------------------
        cur.execute("""
            INSERT INTO subscriptions (
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

        print("[SUBSCRIPTION OK]", subscription_id)

    except Exception as e:
        print("[SUBSCRIPTION ERROR]", str(e))
        conn.rollback()
