import os
import stripe
from dotenv import load_dotenv

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

PRICE_ID = os.getenv("STRIPE_PENNY_PRICE_ID")

def create_checkout():
    session = stripe.checkout.Session.create(
        mode="subscription",  # 🔥 REQUIRED because price is recurring
        line_items=[
            {
                "price": PRICE_ID,
                "quantity": 1,
            }
        ],
        success_url="https://example.com/success",
        cancel_url="https://example.com/cancel",
    )

    print("CHECKOUT URL:", session.url)
    return session.url

if __name__ == "__main__":
    create_checkout()
