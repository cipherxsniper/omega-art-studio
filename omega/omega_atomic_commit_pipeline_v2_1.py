import uuid
from decimal import Decimal

from omega_db_kernel_v1 import OmegaTransaction, insert_event, insert_posting

TREASURY_ACCOUNT = "acd27fe4-1862-48ff-a343-5595cc7ca49b"


def atomic_commit(event):
    try:
        with OmegaTransaction() as cur:

            insert_event(cur, event)

            cur.execute("""
                SELECT COALESCE(MAX(sequence_number), 0) + 1 AS seq
                FROM ledger_postings
            """)
            seq = cur.fetchone()["seq"]

            amount = Decimal(str(event["amount"]))

            treasury_post = {
                "posting_id": str(uuid.uuid4()),
                "event_id": event["event_id"],
                "sequence_number": seq,
                "account_type": "TREASURY",
                "account_id": TREASURY_ACCOUNT,
                "direction": "DEBIT",
                "amount": amount,
                "currency": event["currency"]
            }

            seq += 1

            wallet_post = {
                "posting_id": str(uuid.uuid4()),
                "event_id": event["event_id"],
                "sequence_number": seq,
                "account_type": "WALLET",
                "account_id": event["wallet_id"],
                "direction": "CREDIT",
                "amount": amount,
                "currency": event["currency"]
            }

            insert_posting(cur, treasury_post)
            insert_posting(cur, wallet_post)

        return {"status": "COMMITTED", "event_id": event["event_id"]}

    except Exception as e:
        return {"status": "ROLLED_BACK", "error": str(e)}
