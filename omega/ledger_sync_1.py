import uuid
from datetime import datetime

class LedgerSync:
    def __init__(self, db):
        self.db = db

    def post(self, debit, credit, amount, currency="USD"):
        tx_id = str(uuid.uuid4())

        self.db.execute(
            """
            INSERT INTO ledger_entries (
                id, transaction_id, debit_account,
                credit_account, amount, currency, created_at
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                str(uuid.uuid4()),
                tx_id,
                debit,
                credit,
                amount,
                currency,
                datetime.utcnow()
            )
        )

        self.db.commit()
        return tx_id
