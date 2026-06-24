import logging
from decimal import Decimal
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omega-enforcement-gate")

REQUIRED_FIELDS = {
    "AUTH_CREATED": ["wallet_id", "amount"],
    "AUTH_CAPTURED": ["wallet_id", "amount"],
    "AUTH_REVERSED": ["wallet_id", "amount"],
    "AUTH_EXPIRED": ["wallet_id", "amount"],
    "PAYMENT_CAPTURED": ["wallet_id", "amount", "merchant_id"],
}

def enforce_event(event: dict):
    """
    STRICT ENFORCEMENT GATE (v1)
    - validates schema
    - normalizes numeric fields
    - rejects incomplete events
    """

    if not isinstance(event, dict):
        return {"status": "REJECTED", "reason": "INVALID_EVENT_TYPE"}

    event_type = event.get("event_type")
    event_id = event.get("event_id") or str(uuid.uuid4())
    payload = event.get("payload", {})

    if not event_type:
        return {"status": "REJECTED", "reason": "MISSING_EVENT_TYPE"}

    required = REQUIRED_FIELDS.get(event_type, [])

    # validate required fields
    for field in required:
        if field not in payload:
            logger.warning(f"REJECTED EVENT: {event_id} -> MISSING_FIELD {field}")
            return {
                "status": "REJECTED",
                "event_id": event_id,
                "reason": f"MISSING_FIELD_{field}"
            }

    # normalize numeric values safely
    if "amount" in payload:
        try:
            payload["amount"] = str(Decimal(str(payload["amount"])))
        except Exception:
            return {
                "status": "REJECTED",
                "event_id": event_id,
                "reason": "INVALID_AMOUNT"
            }

    normalized = {
        "status": "ACCEPTED",
        "event": {
            "event_type": event_type,
            "event_id": event_id,
            "payload": payload
        }
    }

    logger.info(f"ACCEPTED EVENT: {event_id}")
    return normalized
