from fastapi import APIRouter
from core.events import create_event, EventType
from core.event_store import publish

router = APIRouter()

@router.post("/transactions/transfer")
def transfer(req: dict):

    event = create_event(
        EventType.TX_REQUESTED,
        {
            "sender": req["sender_wallet"],
            "receiver": req["receiver_wallet"],
            "amount": req["amount"]
        }
    )

    publish(event)

    return {
        "status": "RECEIVED",
        "event_id": event["event_id"]
    }
