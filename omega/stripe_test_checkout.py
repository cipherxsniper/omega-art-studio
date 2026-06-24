import os
from dotenv import load_dotenv
import stripe
import subprocess

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

PRICE_ID = os.getenv("STRIPE_FULL_OPS_PRICE_ID")

if not PRICE_ID:
    raise Exception("Missing FULL OPS PRICE ID")

print("USING PRICE:", PRICE_ID)

session = stripe.checkout.Session.create(
    mode="subscription",
    payment_method_types=["card"],
    line_items=[{
        "price": PRICE_ID,
        "quantity": 1
    }],
    success_url="http://localhost:5050/success",
    cancel_url="http://localhost:5050/cancel",
    metadata={
        "product": "OMEGA_FULL_OPS",
        "tier": "1497"
    }
)

url = session.url
print("CHECKOUT URL:", url)

try:
    subprocess.run(["termux-open-url", url])
except Exception as e:
    print("Open failed:", e)
