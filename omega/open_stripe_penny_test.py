import os
import stripe
import webbrowser
from dotenv import load_dotenv

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

PRICE_ID = os.getenv("STRIPE_PENNY_PRICE_ID")

session = stripe.checkout.Session.create(
    mode="payment",
    line_items=[{
        "price": PRICE_ID,
        "quantity": 1,
    }],
    success_url=os.getenv("STRIPE_SUCCESS_URL"),
    cancel_url=os.getenv("STRIPE_CANCEL_URL"),
)

print("OPENING:", session.url)
webbrowser.open(session.url)
