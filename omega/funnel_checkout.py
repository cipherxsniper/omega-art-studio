import stripe
from infrastructure.env import STRIPE_SECRET_KEY

stripe.api_key = STRIPE_SECRET_KEY

PRICE_MAP = {
    "starter": "price_1TXZ72A5xsR4lvM4aVLVFJAW",
    "growth": "price_1TXZ8RA5xsR4lvM4AMoEXTGs",
    "full": "price_1TXZ9DA5xsR4lvM47e8aC560"
}


def generate_checkout(lead_email, plan="growth"):
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": PRICE_MAP[plan], "quantity": 1}],
        customer_email=lead_email,
        metadata={"plan": plan},
        success_url="https://yourdomain.com/success",
        cancel_url="https://yourdomain.com/cancel"
    )

    return session.url
