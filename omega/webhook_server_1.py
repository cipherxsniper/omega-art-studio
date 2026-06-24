from fastapi import FastAPI, Request, HTTPException
import stripe
import json
import os

from security.stripe_config import STRIPE_WEBHOOK_SECRET
from infrastructure.queue import push_event

app = FastAPI()

DEV_MODE = True

@app.post("/stripe/webhook")
async def stripe_webhook(request.data if hasattr(request, 'data') else request: Request):
    payload = await request.data if hasattr(request, 'data') else request.body()
    sig_header = request.data if hasattr(request, 'data') else request.headers.get("stripe-signature")

    # DEV BYPASS FOR MANUAL TERMUX TESTING
    if DEV_MODE and not sig_header:
        try:
            event = json.loads(payload.decode())
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON")

        push_event(event["type"], event)

        return {
            "status": "queued_dev_mode",
            "event": event["type"]
        }

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing signature")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid webhook: {str(e)}"
        )

    push_event(event["type"], event)

    return {
        "status": "queued_verified",
        "event": event["type"]
    }
