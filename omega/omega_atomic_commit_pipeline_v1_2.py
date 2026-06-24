import uuid
import psycopg2

from decimal import Decimal
from datetime import datetime, UTC

DB_NAME = "omega_bank"
DB_USER = "omega"

TREASURY_ACCOUNT = "11111111-1111-1111-1111-111111111111"

EVENT_TYPE = "PAYMENT_CAPTURED"
AGGREGATE_TYPE = "PAYMENT"


def db():
    return psycopg2.connect(
        database=DB_NAME,
        user=DB_USER
    )


def next_sequence(cur):
    cur.execute("""
        SELECT COALESCE(MAX(sequence_number), 0) + 1
        FROM ledger_postings
    """)
    return cur.fetchone()[0]


def build_event():
    event_id = str(uuid.uuid4())

    return {
        "event_id": event_id,
        "event_type": EVENT_TYPE,
        "aggregate_id": str(uuid.uuid4()),
        "aggregate_type": AGGREGATE_TYPE,
        "timestamp": datetime.now(UTC).isoformat(),
        "merchant_id": "omega_merchant",
        "wallet_id": "00000000-0000-0000-0000-000000000000",
        "amount": "25.00",
        "currency": "USD",
        "payload": {
            "source": "atomic_pipeline_v1"
        },
        "version": 1
    }


def insert_event(cur, event):
    cur.execute(
        """
        INSERT INTO omega_events (
            event_id,
            event_type,
            aggregate_id,
            aggregate_type,
            payload,
            timestamp,
            merchant_id,
            wallet_id,
            amount,
            currency,
            version
        )
        VALUES (
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
        )
        """,
        (
            event["event_id"],
            event["event_type"],
            event["aggregate_id"],
            event["aggregate_type"],
            psycopg2.extras.Json(event["payload"]),
            event["timestamp"],
            event["merchant_id"],
            event["wallet_id"],
            Decimal(event["amount"]),
            event["currency"],
            event["version"]
        )
    )


def insert_postings(cur, event):
    amount = Decimal(event["amount"])

    seq = next_sequence(cur)

    debit_posting_id = str(uuid.uuid4())
    credit_posting_id = str(uuid.uuid4())

    # DEBIT TREASURY
    cur.execute(
        """
        INSERT INTO ledger_postings (
            posting_id,
            event_id,
            sequence_number,
            account_type,
            account_id,
            direction,
            amount,
            currency
        )
        VALUES (
            %s,%s,%s,%s,%s,%s,%s,%s
        )
        """,
        (
            debit_posting_id,
            event["event_id"],
            seq,
            "TREASURY",
            TREASURY_ACCOUNT,
            "DEBIT",
            amount,
            event["currency"]
        )
    )

    # CREDIT WALLET
    cur.execute(
        """
        INSERT INTO ledger_postings (
            posting_id,
            event_id,
            sequence_number,
            account_type,
            account_id,
            direction,
            amount,
            currency
        )
        VALUES (
            %s,%s,%s,%s,%s,%s,%s,%s
        )
        """,
        (
            credit_posting_id,
            event["event_id"],
            seq + 1,
            "WALLET",
            event["wallet_id"],
            "CREDIT",
            amount,
            event["currency"]
        )
    )


def commit_pipeline():
    conn = db()
    conn.autocommit = False

    try:
        cur = conn.cursor()

        event = build_event()

        insert_event(cur, event)

        insert_postings(cur, event)

        conn.commit()

        return {
            "status": "COMMITTED",
            "event_id": event["event_id"]
        }

    except Exception as e:
        conn.rollback()

        return {
            "status": "ROLLED_BACK",
            "error": str(e)
        }

    finally:
        conn.close()


if __name__ == "__main__":
    print("🔒 OMEGA ATOMIC COMMIT PIPELINE v1")
    print(commit_pipeline())
