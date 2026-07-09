class SettlementEngine:

    def __init__(self, ledger_engine):
        self.ledger_engine = ledger_engine

    def settle(
        self,
        transaction_id,
        sender_wallet,
        receiver_wallet,
        amount
    ):

        self.ledger_engine.commit_entry(
            transaction_id=transaction_id,
            debit_account=sender_wallet,
            credit_account=receiver_wallet,
            amount=amount
        )

        return {
            "status": "SETTLED",
            "transaction_id": transaction_id
        }
