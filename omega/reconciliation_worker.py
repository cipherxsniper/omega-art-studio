import time

from database.db import SessionLocal
from core.reconciliation import ReconciliationEngine


def main():

    while True:

        db = SessionLocal()

        try:

            reconciliation = ReconciliationEngine(db)

            result = reconciliation.reconcile()

            print("\\n[RECONCILIATION REPORT]")
            print(result)

        finally:
            db.close()

        time.sleep(30)


if __name__ == "__main__":
    main()
