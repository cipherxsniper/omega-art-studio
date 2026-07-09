import stripe
from infrastructure.env import STRIPE_SECRET_KEY

stripe.api_key = STRIPE_SECRET_KEY


PRICE_MAP = {
    "starter": "price_1TXZ72A5xsR4lvM4aVLVFJAW",
    "growth": "price_1TXZ8RA5xsR4lvM4AMoEXTGs",
    "full": "price_1TXZ9DA5xsR4lvM47e8aC560"
}


def create_checkout_session(plan, success_url, cancel_url):
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": PRICE_MAP[plan], "quantity": 1}],
        metadata={"plan": plan},
        success_url=success_url,
        cancel_url=cancel_url
    )
    return session.url
