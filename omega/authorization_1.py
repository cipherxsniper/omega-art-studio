from core.ledger import LedgerEngine
from core.holds import HoldManager

class AuthorizationEngine:

    def __init__(self):
        self.ledger = LedgerEngine()
        self.holds = HoldManager()

    def compute_balance(self, wallet_id):
        balance = 0

        for row in self.ledger.get_all():
            t = row[1]
            payload = __import__("json").loads(row[2])

            if t == "TX_SETTLED":
                if payload["sender_wallet"] == wallet_id:
                    balance -= payload["amount"]
                if payload["receiver_wallet"] == wallet_id:
                    balance += payload["amount"]

        return balance

    def available_balance(self, wallet_id):
        return self.compute_balance(wallet_id) - self.holds.total_active_holds(wallet_id)

    def can_spend(self, wallet_id, amount):
        return self.available_balance(wallet_id) >= amount
