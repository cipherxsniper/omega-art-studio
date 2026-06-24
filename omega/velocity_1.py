from sqlalchemy import text


class VelocityEngine:

    def __init__(self, db):
        self.db = db

    def increment(self, wallet_id):

        exists = self.db.execute(
            text("""
            SELECT transaction_count
            FROM velocity_tracking
            WHERE wallet_id = :wallet_id
            """),
            {
                "wallet_id": wallet_id
            }
        ).fetchone()

        if exists:

            self.db.execute(
                text("""
                UPDATE velocity_tracking
                SET
                    transaction_count =
                        transaction_count + 1,

                    updated_at = NOW()

                WHERE wallet_id = :wallet_id
                """),
                {
                    "wallet_id": wallet_id
                }
            )

        else:

            self.db.execute(
                text("""
                INSERT INTO velocity_tracking (
                    wallet_id,
                    transaction_count
                )
                VALUES (
                    :wallet_id,
                    1
                )
                """),
                {
                    "wallet_id": wallet_id
                }
            )

        self.db.commit()

    def get_velocity(self, wallet_id):

        result = self.db.execute(
            text("""
            SELECT transaction_count
            FROM velocity_tracking
            WHERE wallet_id = :wallet_id
            """),
            {
                "wallet_id": wallet_id
            }
        ).fetchone()

        if not result:
            return 0

        return int(result[0])
