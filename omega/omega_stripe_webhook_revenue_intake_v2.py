#!/usr/bin/env python3

import json
from omega_event_bus_core_v1 import connect_db
from omega_stripe_revenue_correctness_v1 import process_subscription_revenue
from omega_subscription_persistence_engine_v1 import persist_subscription_state

def handle_stripe_event(event):
    conn = connect_db()

    # 1. Correct revenue state first (idempotent)
    revenue_state = process_subscription_revenue(conn)

    # 2. Persist subscription state snapshot (NEW LAYER)
    persist_subscription_state(conn, {
        "active_subscriptions": revenue_state.get("active", 0),
        "mrr": revenue_state.get("mrr", 0.0),
        "event": event
    })

    conn.commit()
    conn.close()

    return revenue_state

if __name__ == "__main__":
    print("[OMEGA STRIPE PIPELINE v2] READY - waiting for webhook events")
