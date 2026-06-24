import uuid
import hashlib

class UserManager:

    def __init__(self, db):
        self.db = db

    def create_user(self, name, pin):

        user_id = str(uuid.uuid4())
        pin_hash = hashlib.sha256(pin.encode()).hexdigest()

        self.db.execute(
            """
            INSERT INTO users (id, name, pin_hash)
            VALUES (:id, :name, :pin_hash)
            """,
            {"id": user_id, "name": name, "pin_hash": pin_hash}
        )

        self.db.commit()
        return user_id

    def verify_pin(self, user_id, pin):

        result = self.db.execute(
            "SELECT pin_hash FROM users WHERE id = :id",
            {"id": user_id}
        ).fetchone()

        if not result:
            return False

        return hashlib.sha256(pin.encode()).hexdigest() == result[0]
