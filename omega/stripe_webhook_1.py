from fastapi import APIRouter, Request
from core.redis_bus import publish
import hashlib

router = APIRouter()

def idempotency(event):
    raw = f"{event.get('id')}:{event.get('type')}"
    return hashlib.sha256(raw.encode()).hexdigest()

@router.post("/stripe/webhook")
async def webhook(req: Request):
    event = await req.json()

    publish(
        "STRIPE_EVENT",
        event,
        idempotency_key=idempotency(event)
    )

    return {"ok": True}
