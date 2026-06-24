import uuid
from datetime import datetime


class TransactionManager:

    def __init__(self, db):
        self.db = db

    def create_transaction(
        self,
        wallet_id,
        amount,
        status,
        merchant=None,
        risk_score=0
    ):

        transaction_id = str(uuid.uuid4())

        self.db.execute(
            """
            INSERT INTO transactions (
                id,
                wallet_id,
                amount,
                status,
                merchant,
                risk_score,
                created_at
            )
            VALUES (
                :id,
                :wallet_id,
                :amount,
                :status,
                :merchant,
                :risk_score,
                :created_at
            )
            """,
            {
                "id": transaction_id,
                "wallet_id": wallet_id,
                "amount": amount,
                "status": status,
                "merchant": merchant,
                "risk_score": risk_score,
                "created_at": datetime.utcnow()
            }
        )

        self.db.commit()

        return transaction_id

    def update_status(
        self,
        transaction_id,
        status
    ):

        self.db.execute(
            """
            UPDATE transactions
            SET status = :status
            WHERE id = :transaction_id
            """,
            {
                "status": status,
                "transaction_id": transaction_id
            }
        )

        self.db.commit()
