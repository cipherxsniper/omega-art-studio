import json

class BalanceEngine:

    def __init__(self, ledger):
        self.ledger = ledger

    def compute_balance(self, wallet_id):
        balance = 0.0

        for row in self.ledger.get_all():
            event_type = row[1]
            payload = json.loads(row[2])

            if event_type == "TX_SETTLED":

                if payload.get("receiver_wallet") == wallet_id:
                    balance += float(payload["amount"])

                if payload.get("sender_wallet") == wallet_id:
                    balance -= float(payload["amount"])

        return balance
