from core.idempotency import IdempotencyStore
from core.ledger_sync import LedgerSync
from core.event_store import EventStore

class StripeBridge:

    def __init__(self, db):
        self.db = db
        self.idempotency = IdempotencyStore()
        self.ledger = LedgerSync(db)
        self.events = EventStore(db)

    def handle_event(self, event):

        try:
            if not event:
                return {"status": "IGNORED_EMPTY_EVENT"}

            event_id = event.get("id")
            event_type = event.get("type")
            data = (event.get("data") or {}).get("object") or {}

            if not event_id or not event_type:
                return {"status": "INVALID_EVENT"}

            # idempotency guard
            if self.idempotency.seen(event_id):
                return {"status": "IGNORED_DUPLICATE"}

            self.idempotency.mark(event_id)

            # audit log
            self.events.append(event_id, event_type, data)

            # payment success
            if event_type == "payment_intent.succeeded":
                amount = float(data.get("amount_received", 0)) / 100

                self.ledger.post(
                    debit="STRIPE_CASH_ACCOUNT",
                    credit="OMEGA_TREASURY",
                    amount=amount
                )

            # payout event
            elif event_type == "payout.paid":
                amount = float(data.get("amount", 0)) / 100

                self.ledger.post(
                    debit="OMEGA_TREASURY",
                    credit="STRIPE_PAYOUT",
                    amount=amount
                )

            return {"status": "PROCESSED", "event_id": event_id}

        except Exception as e:
            return {
                "status": "FAILED_SAFE",
                "error": str(e)
            }
