"""
OMEGA RISK ENGINE
Pure Python logic layer (NO SQL HERE)
"""

class RiskEngine:

    def __init__(self, ledger_reader):
        self.ledger = ledger_reader

    # -------------------------
    # BALANCE CHECK (OVERDRAFT RULE)
    # -------------------------
    def can_spend(self, wallet_id, amount, overdraft_limit=0):
        balance = self.get_balance(wallet_id)
        return (balance - amount) >= -overdraft_limit

    # -------------------------
    # REAL BALANCE REPLAY
    # -------------------------
    def get_balance(self, wallet_id):
        balance = 0.0

        for row in self.ledger.get_all():
            event_type = row[1]
            payload = row[2]

            # assume payload already dict OR JSON string
            if isinstance(payload, str):
                import json
                payload = json.loads(payload)

            if event_type == "TX_SETTLED":

                if payload.get("receiver_wallet") == wallet_id:
                    balance += float(payload["amount"])

                if payload.get("sender_wallet") == wallet_id:
                    balance -= float(payload["amount"])

        return balance


# -------------------------
# CREDIT ISSUANCE LOGIC
# -------------------------

def issue_credit(reserve_balance, liabilities, amount, create_transaction_fn, target_wallet):
    """
    Reserve-backed credit issuance (bank rule)
    """

    if liabilities + amount > reserve_balance:
        raise Exception("INSUFFICIENT RESERVES")

    return create_transaction_fn([
        {
            "type": "DEBIT",
            "wallet": "OMEGA_RESERVE",
            "amount": amount
        },
        {
            "type": "CREDIT",
            "wallet": target_wallet,
            "amount": amount
        }
    ])
