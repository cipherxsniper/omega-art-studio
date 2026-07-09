import uuid
from datetime import datetime

class PendingSettlementStore:
    def __init__(self, db):
        self.db = db

    def create(self, tx_id, sender, receiver, amount):
        settlement_id = str(uuid.uuid4())

        self.db.execute(
            """
            INSERT INTO pending_settlements (
                id, transaction_id, sender_wallet, receiver_wallet,
                amount, status, created_at, updated_at
            )
            VALUES (
                :id, :tx, :sender, :receiver,
                :amount, 'PENDING', :created_at, :updated_at
            )
            """,
            {
                "id": settlement_id,
                "tx": tx_id,
                "sender": sender,
                "receiver": receiver,
                "amount": amount,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        )

        self.db.commit()
        return settlement_id
