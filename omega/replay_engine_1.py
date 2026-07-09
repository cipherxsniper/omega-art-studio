import json

class ReplayEngine:

    def __init__(self, ledger):
        self.ledger = ledger

    def rebuild_state(self):
        state = {}

        for row in self.ledger.get_all():
            event_type = row[1]
            payload = json.loads(row[2])

            if event_type == "TX_SETTLED":
                sender = payload["sender_wallet"]
                receiver = payload["receiver_wallet"]
                amount = float(payload["amount"])

                state[sender] = state.get(sender, 0) - amount
                state[receiver] = state.get(receiver, 0) + amount

        return state
