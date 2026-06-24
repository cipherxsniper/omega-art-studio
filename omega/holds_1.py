from sqlalchemy import text


class HoldManager:
    def __init__(self, db):
        self.db = db

    def place_hold(self, wallet_id, amount):
        wallet = self.db.execute(
            text("""
                SELECT *
                FROM wallets
                WHERE wallet_id = :wallet_id
            """),
            {"wallet_id": wallet_id}
        ).fetchone()

        if not wallet:
            raise Exception("Wallet not found")

        balance = float(wallet.balance)

        if balance < amount:
            raise Exception("Insufficient funds")

        self.db.execute(
            text("""
                UPDATE wallets
                SET held_balance = held_balance + :amount
                WHERE wallet_id = :wallet_id
            """),
            {
                "wallet_id": wallet_id,
                "amount": amount
            }
        )

        self.db.commit()


hold_manager = HoldManager
