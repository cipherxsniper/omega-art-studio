from core.events import create_event, EventType
from core.event_store import publish

def fund(amount):
    event = create_event(
        EventType.TX_SETTLED,
        {
            "sender_wallet": "TREASURY_RESERVE",
            "receiver_wallet": "SYSTEM_LIABILITY_POOL",
            "amount": amount
        }
    )
    publish(event)
    print("Treasury funded via ledger event:", amount)

fund(12000000.0)
