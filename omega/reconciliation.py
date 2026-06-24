from sqlalchemy import text


class ReconciliationEngine:

    def __init__(self, db):
        self.db = db

    def reconcile(self):

        reserves = self.db.execute(
            text(
                "SELECT COALESCE(SUM(reserve_balance),0) FROM treasury_accounts"
            )
        ).scalar()

        liabilities = self.db.execute(
            text(
                "SELECT COALESCE(SUM(available_balance),0) FROM wallets"
            )
        ).scalar()

        difference = reserves - liabilities

        return {
            "reserves": float(reserves),
            "liabilities": float(liabilities),
            "difference": float(difference),
            "solvent": difference >= 0
        }
