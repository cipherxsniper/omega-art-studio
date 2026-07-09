import os
import json
import stripe

from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import text

from database.db import SessionLocal
from core.event_log import EventLog

router = APIRouter()

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

@router.post("/stripe/webhook")
async def stripe_webhook(request: Request):

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # 1. VERIFY STRIPE SIGNATURE (REAL SECURITY LAYER)
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid webhook: {str(e)}")

    db = SessionLocal()
    event_log = EventLog(db)

    event_id = event.get("id")
    event_type = event.get("type")

    # 2. IDEMPOTENCY CHECK (NO DOUBLE PROCESSING)
    existing = db.execute(
        text("""
            SELECT 1 FROM audit_logs
            WHERE metadata->>'stripe_event_id' = :event_id
            LIMIT 1
        """),
        {"event_id": event_id}
    ).fetchone()

    if existing:
        return {"ok": True, "result": "IGNORED_DUPLICATE"}

    # 3. EXTRACT STRIPE DATA
    data_object = event["data"]["object"]

    amount = data_object.get("amount_received") or data_object.get("amount", 0)

    # 4. WRITE IMMUTABLE EVENT LOG
    event_log.append(
        event_type="STRIPE_EVENT_RECEIVED",
        payload={
            "stripe_event_id": event_id,
            "stripe_type": event_type,
            "amount": amount,
            "raw": data_object
        },
        idempotency_key=event_id
    )

    # 5. MAP STRIPE → OMEGA TRANSACTION INTENT
    if event_type == "payment_intent.succeeded":

        tx_id = data_object.get("id")

        db.execute(
            text("""
                INSERT INTO pending_settlements (
                    id,
                    transaction_id,
                    sender_wallet,
                    receiver_wallet,
                    amount,
                    status
                )
                VALUES (
                    gen_random_uuid(),
                    :tx_id,
                    'STRIPE_EXTERNAL',
                    'OMEGA_TREASURY',
                    :amount,
                    'PENDING'
                )
            """),
            {
                "tx_id": tx_id,
                "amount": amount / 100.0
            }
        )

        db.commit()

        return {"ok": True, "result": "INJECTED_TO_LEDGER"}

    return {"ok": True, "result": "IGNORED_EVENT_TYPE"}
