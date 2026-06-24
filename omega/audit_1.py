import uuid

from sqlalchemy import text


class AuditLogger:

    def __init__(self, db):
        self.db = db

    def log(
        self,
        action,
        metadata
    ):

        self.db.execute(
            text("""
            INSERT INTO audit_logs (
                id,
                action,
                metadata
            )
            VALUES (
                :id,
                :action,
                :metadata
            )
            """),
            {
                "id": str(uuid.uuid4()),
                "action": action,
                "metadata": metadata
            }
        )

        self.db.commit()
