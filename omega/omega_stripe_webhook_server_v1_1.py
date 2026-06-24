import os
import json
import logging

from dotenv import load_dotenv
from flask import Flask, request, jsonify

import stripe

from omega_enforcement_gate_v1 import enforce_event
from omega_event_factory import normalize_stripe_event
from omega_transactional_event_store import append_event

# =========================
# ENV LOAD (CRITICAL FIX)
# =========================
load_dotenv()

STRIPE_SECRET = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

if not STRIPE_SECRET:
    raise Exception("Missing STRIPE_SECRET_KEY")

if not WEBHOOK_SECRET:
    raise Exception("Missing STRIPE_WEBHOOK_SECRET")

stripe.api_key = STRIPE_SECRET

# =========================
# LOGGING
# =========================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omega-stripe-webhook")

# =========================
# APP
# =========================
app = Flask(__name__)

# =========================
# SINGLE INGESTION PIPELINE
# =========================
def process_stripe_event(event_json):
    """
    ALL events (real/sim/test) MUST enter here AFTER verification.
    NO branching logic elsewhere.
    """

    # 1. Normalize to Omega schema
    omega_event = normalize_stripe_event(event_json)

    # 2. Enforcement Gate (STRICT)
    result = enforce_event(omega_event)

    if result["status"] != "ACCEPTED":
        logger.warning(f"REJECTED EVENT: {result}")
        return {"status": "REJECTED", "reason": result}

    # 3. Commit to event store
    append_event(omega_event)

    logger.info(f"ACCEPTED EVENT: {omega_event['event_id']}")

    return {"status": "ACCEPTED", "event": omega_event}


# =========================
# STRIPE WEBHOOK ENDPOINT
# =========================
@app.route("/stripe/webhook", methods=["POST"])
def stripe_webhook():

    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")

    if not sig_header:
        return jsonify({"status": "ERROR", "error": "Missing Stripe signature"}), 400

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            WEBHOOK_SECRET
        )
    except Exception as e:
        return jsonify({"status": "ERROR", "error": str(e)}), 400

    # CRITICAL: single pipeline entry
    result = process_stripe_event(event)

    return jsonify(result)


# =========================
# HEALTH CHECK
# =========================
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "OK", "service": "omega-stripe-webhook-v1"})


# =========================
# RUN SERVER
# =========================
if __name__ == "__main__":
    logger.info("🔗 Omega Stripe Webhook Server v1 starting...")
    app.run(host="0.0.0.0", port=8000)


from webhook_route_patch import webhook_route

webhook_route(app, stripe, request, STRIPE_WEBHOOK_SECRET, jsonify)

