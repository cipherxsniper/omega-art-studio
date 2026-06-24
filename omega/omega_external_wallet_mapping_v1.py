"""
Stripe-only external mapping layer.
NO crypto. NO USDT. NO MEXC.
"""

STRIPE_ACCOUNT_MAP = {
    "stripe": "OMEGA_STRIPE_TREASURY",
    "customers": "OMEGA_CUSTOMER_POOL",
    "revenue": "REVENUE",
    "platform": "OMEGA_SYSTEM_CAPITAL"
}

def map_stripe_customer(customer_id):
    return f"STRIPE_CUSTOMER::{customer_id}"
