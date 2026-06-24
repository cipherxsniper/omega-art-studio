from sqlalchemy import text

class StateStore:
    def __init__(self, db):
        self.db = db

    def create(self, tx_id, state):
        self.db.execute(
            text("""
                INSERT INTO transactions (id, status)
                VALUES (:id, :status)
            """),
            {"id": tx_id, "status": state}
        )
        self.db.commit()

    def update(self, tx_id, state):
        self.db.execute(
            text("""
                UPDATE transactions
                SET status = :status
                WHERE id = :id
            """),
            {"id": tx_id, "status": state}
        )
        self.db.commit()
