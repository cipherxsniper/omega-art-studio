import uuid
from datetime import datetime

class EventType:
    TX_REQUESTED = "TX_REQUESTED"
    TX_AUTHORIZED = "TX_AUTHORIZED"
    TX_HELD = "TX_HELD"
    TX_SETTLED = "TX_SETTLED"
    STRIPE_PAYMENT = "STRIPE_PAYMENT"


def create_event(event_type: str, payload: dict):
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "payload": payload,
        "timestamp": datetime.utcnow().isoformat()
    }
