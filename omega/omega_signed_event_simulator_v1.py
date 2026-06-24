import os
import json
import time
import hmac
import hashlib
import requests
from dotenv import load_dotenv

load_dotenv()

WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

if not WEBHOOK_SECRET:
    raise Exception("Missing STRIPE_WEBHOOK_SECRET")

# =========================================
# STRIPE-STYLE EVENT
# =========================================
event = {
    "id": "evt_omega_test_001",
    "object": "event",
    "type": "payment_intent.succeeded",
    "created": int(time.time()),
    "data": {
        "object": {
            "id": "pi_omega_test_001",
            "object": "payment_intent",
            "amount": 29,
            "currency": "usd",
            "customer": "00000000-0000-0000-0000-000000000000",
            "metadata": {
                "wallet_id": "00000000-0000-0000-0000-000000000000",
                "merchant_id": "11111111-1111-1111-1111-111111111111"
            }
        }
    }
}

payload = json.dumps(event)

# =========================================
# STRIPE SIGNATURE
# =========================================
timestamp = str(int(time.time()))

signed_payload = f"{timestamp}.{payload}"

signature = hmac.new(
    WEBHOOK_SECRET.encode(),
    signed_payload.encode(),
    hashlib.sha256
).hexdigest()

stripe_signature = f"t={timestamp},v1={signature}"

headers = {
    "Content-Type": "application/json",
    "Stripe-Signature": stripe_signature
}

print("🚀 Sending signed Stripe-style event...")
print("🔐 Signature:", stripe_signature)

response = requests.post(
    "http://127.0.0.1:8000/stripe/webhook",
    data=payload,
    headers=headers
)

print("STATUS:", response.status_code)
print("RESPONSE:", response.text)
