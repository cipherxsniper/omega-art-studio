import uuid
from datetime import datetime

class EventLog:
    def __init__(self, db):
        self.db = db

    def append(self, event_type, payload, idempotency_key):
        event_id = str(uuid.uuid4())

        self.db.execute(
            """
            INSERT INTO audit_logs (id, action, metadata, created_at)
            VALUES (:id, :action, :metadata, :created_at)
            """,
            {
                "id": event_id,
                "action": event_type,
                "metadata": payload,
                "created_at": datetime.utcnow()
            }
        )

        self.db.commit()

        return event_id
