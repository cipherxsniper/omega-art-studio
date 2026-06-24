from fastapi import APIRouter, Request
from core.stripe_bridge import StripeBridge
from database.db import SessionLocal

router = APIRouter()

@router.post("/stripe/webhook")
async def stripe_webhook(request: Request):

    payload = await request.json()

    db = SessionLocal()
    bridge = StripeBridge(db)

    result = bridge.handle_event(payload)

    return {
        "ok": True,
        "result": result
    }
