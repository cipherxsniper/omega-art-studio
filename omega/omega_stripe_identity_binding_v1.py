#!/usr/bin/env python3

"""
OMEGA STRIPE IDENTITY BINDING ENGINE V1
Fixes UNKNOWN_CUSTOMER problem
"""

import json
import time

def extract_stripe_identity(session, event):

    # priority 1: checkout.session
    customer_id = session.get("customer")

    # priority 2: payment_intent fallback
    if not customer_id:
        pi = session.get("payment_intent", {})
        if isinstance(pi, dict):
            customer_id = pi.get("customer")

    # priority 3: event-level fallback
    if not customer_id:
        customer_id = event.get("customer")

    # fallback guard
    if not customer_id:
        customer_id = "UNKNOWN_CUSTOMER"

    return customer_id


def extract_price_id(session):

    return (
        session.get("metadata", {}).get("price_id")
        or session.get("subscription_details", {}).get("price", {}).get("id")
        or session.get("display_items", [{}])[0].get("price", {}).get("id")
    )


def normalize_subscription_payload(session, event):

    return {
        "subscription_id": session.get("subscription"),
        "customer_id": extract_stripe_identity(session, event),
        "price_id": extract_price_id(session),
        "status": "active",
        "current_period_start": session.get("current_period_start", 0),
        "current_period_end": session.get("current_period_end", 0),
        "cancel_at_period_end": 0,
        "created_at": time.time()
    }


print("[OMEGA] Stripe identity binding engine loaded")
