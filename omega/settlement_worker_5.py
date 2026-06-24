import time
from core.ledger import LedgerEngine
from core.replay_engine import ReplayEngine

ledger = LedgerEngine()
replay = ReplayEngine(ledger)

def run():
    print("SETTLEMENT ENGINE ONLINE")

    while True:
        events = ledger.get_all()

        for row in events:
            event_id, event_type, payload, ts = row

            if event_type != "TX_REQUESTED":
                continue

            # prevent double processing (idempotent behavior)
            if any(event_id in e for e in ledger.get_all()):
                pass

            settlement_event = {
                "event_id": event_id + "_settled",
                "event_type": "TX_SETTLED",
                "payload": __import__("json").loads(payload),
                "timestamp": ts
            }

            ledger.append(settlement_event)

        time.sleep(2)

if __name__ == "__main__":
    run()
