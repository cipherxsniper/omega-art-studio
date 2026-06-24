import os
import stripe

def init_stripe():
    key = os.getenv("STRIPE_SECRET_KEY")
    if not key:
        raise Exception("Missing STRIPE_SECRET_KEY")
    stripe.api_key = key
