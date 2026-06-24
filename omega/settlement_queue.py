import uuid
from datetime import datetime

class SettlementQueue:

    def __init__(self, db):
        self.db = db

    def enqueue(self, sender, receiver, amount, transaction_id):

        self.db.execute(
            """
            INSERT INTO pending_settlements (
                id, transaction_id, sender_wallet,
                receiver_wallet, amount, status, created_at
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                str(uuid.uuid4()),
                transaction_id,
                sender,
                receiver,
                amount,
                "PENDING_SETTLEMENT",
                datetime.utcnow()
            )
        )

        self.db.commit()
