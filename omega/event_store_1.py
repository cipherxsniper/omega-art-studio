from core.idempotency import IdempotencyStore
from core.ledger import LedgerEngine

idemp = IdempotencyStore()
ledger = LedgerEngine()

def publish(event):
    key = event["event_id"]

    if idemp.exists(key):
        return {"status": "DUPLICATE_IGNORED"}

    idemp.mark(key)
    ledger.append(event)

    return {"status": "ACCEPTED"}
