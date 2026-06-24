import os
import json
import logging
import psycopg2
import stripe
from datetime import datetime

from omega_enforcement_gate_v1 import enforce_event

# =========================
# LOAD .ENV FILE (CRITICAL FIX)
# =========================
def load_env_file(path=".env"):
    if not os.path.exists(path):
        return

    with open(path, "r") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

load_env_file()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omega-stripe-bridge")

# =========================
# CONFIG
# =========================
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

if not STRIPE_SECRET_KEY:
    raise Exception("Missing STRIPE_SECRET_KEY")

if not STRIPE_WEBHOOK_SECRET:
    raise Exception("Missing STRIPE_WEBHOOK_SECRET")

stripe.api_key = STRIPE_SECRET_KEY


# =========================
# EVENT INSERT
# =========================
def insert_event(event):
    conn = psycopg2.connect(database="omega_bank", user="omega")
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO omega_events (event_type, event_id, payload, created_at)
        VALUES (%s, %s, %s, %s)
    """, (
        event["event_type"],
        event["event_id"],
        json.dumps(event["payload"]),
        datetime.utcnow()
    ))

    conn.commit()
    conn.close()


# =========================
# NORMALIZER
# =========================
def normalize_stripe_event(event):
    event_type = event["type"]
    data = event["data"]["object"]

    base = {
        "event_id": event["id"],
        "event_type": None,
        "payload": {}
    }

    if event_type == "payment_intent.succeeded":
        base["event_type"] = "PAYMENT_CAPTURED"
        base["payload"] = {
            "amount": data.get("amount_received", 0) / 100,
            "currency": data.get("currency"),
            "wallet_id": data.get("metadata", {}).get("wallet_id"),
            "merchant_id": data.get("metadata", {}).get("merchant_id")
        }

    elif event_type == "payment_intent.payment_failed":
        base["event_type"] = "PAYMENT_FAILED"
        base["payload"] = {
            "reason": data.get("last_payment_error", {}).get("message", "unknown"),
            "wallet_id": data.get("metadata", {}).get("wallet_id")
        }

    elif event_type == "charge.refunded":
        base["event_type"] = "PAYMENT_REVERSED"
        base["payload"] = {
            "amount": data.get("amount_refunded", 0) / 100,
            "wallet_id": data.get("metadata", {}).get("wallet_id")
        }

    else:
        base["event_type"] = "UNKNOWN_STRIPE_EVENT"
        base["payload"] = {"raw_type": event_type}

    return base


# =========================
# WEBHOOK HANDLER
# =========================
def handle_stripe_webhook(payload, sig_header):
    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            STRIPE_WEBHOOK_SECRET
        )

        omega_event = normalize_stripe_event(event)

        result = enforce_event(omega_event)

        if result["status"] != "ACCEPTED":
            logger.warning(f"REJECTED EVENT: {result}")
            return {"status": "REJECTED"}

        insert_event(omega_event)

        logger.info(f"ACCEPTED STRIPE EVENT: {omega_event['event_id']}")

        return {"status": "OK"}

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return {"status": "ERROR", "error": str(e)}


# =========================
# CLI TEST
# =========================
if __name__ == "__main__":
    print("🔗 Omega Stripe Bridge v1 (ENV FIXED)")
    print("📡 Ready for webhook ingestion")
