import uuid
from decimal import Decimal
from datetime import datetime, UTC

import psycopg2
import psycopg2.extras

DB_NAME = "omega_bank"
DB_USER = "omega"


def omega_address():
    return str(uuid.uuid4())


GENESIS_ACCOUNTS = [
    {
        "account_name": "OMEGA_TREASURY",
        "account_type": "TREASURY",
        "account_id": omega_address(),
        "balance": Decimal("12500000000.00")
    },
    {
        "account_name": "THOMAS_LEE_HARVEY",
        "account_type": "FOUNDER",
        "account_id": omega_address(),
        "balance": Decimal("50000000.00")
    },
    {
        "account_name": "OMEGA_CREDIT",
        "account_type": "CREDIT",
        "account_id": omega_address(),
        "balance": Decimal("250000000.00")
    },
    {
        "account_name": "OMEGA_INVESTMENT",
        "account_type": "INVESTMENT",
        "account_id": omega_address(),
        "balance": Decimal("500000000.00")
    }
]

SYSTEM_ACCOUNT = omega_address()


def connect():
    return psycopg2.connect(
        database=DB_NAME,
        user=DB_USER
    )


def next_sequence(cur):
    cur.execute(
        """
        SELECT COALESCE(MAX(sequence_number), 0) + 1
        FROM ledger_postings
        """
    )

    return cur.fetchone()[0]


def insert_event(cur, event):
    cur.execute(
        """
        INSERT INTO omega_events (
            event_id,
            event_type,
            aggregate_id,
            aggregate_type,
            payload,
            created_at,
            timestamp,
            merchant_id,
            wallet_id,
            amount,
            currency,
            version
        )
        VALUES (
            %s,%s,%s,%s,%s,
            NOW(),
            %s,
            %s,%s,%s,%s,%s
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
            event["amount"],
            event["currency"],
            event["version"]
        )
    )


def insert_posting(
    cur,
    posting_id,
    event_id,
    sequence_number,
    account_type,
    account_id,
    direction,
    amount,
    currency
):
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
            posting_id,
            event_id,
            sequence_number,
            account_type,
            account_id,
            direction,
            amount,
            currency
        )
    )


def create_genesis():
    conn = connect()

    try:
        conn.autocommit = False

        cur = conn.cursor()

        print("\n🏦 OMEGA CANONICAL ACCOUNTS\n")

        for acct in GENESIS_ACCOUNTS:

            event_id = str(uuid.uuid4())

            event = {
                "event_id": event_id,
                "event_type": "GENESIS_ISSUED",
                "aggregate_id": acct["account_id"],
                "aggregate_type": acct["account_type"],
                "timestamp": datetime.now(UTC).isoformat(),
                "merchant_id": "omega_genesis",
                "wallet_id": acct["account_id"],
                "amount": str(acct["balance"]),
                "currency": "USD",
                "payload": {
                    "account_name": acct["account_name"],
                    "genesis": True
                },
                "version": 1
            }

            insert_event(cur, event)

            seq = next_sequence(cur)

            # SYSTEM CREDIT
            insert_posting(
                cur,
                str(uuid.uuid4()),
                event_id,
                seq,
                "SYSTEM",
                SYSTEM_ACCOUNT,
                "CREDIT",
                acct["balance"],
                "USD"
            )

            seq += 1

            # ACCOUNT DEBIT
            insert_posting(
                cur,
                str(uuid.uuid4()),
                event_id,
                seq,
                acct["account_type"],
                acct["account_id"],
                "DEBIT",
                acct["balance"],
                "USD"
            )

            print(f"ACCOUNT: {acct['account_name']}")
            print(f"TYPE:    {acct['account_type']}")
            print(f"ADDRESS: {acct['account_id']}")
            print(f"BALANCE: ${acct['balance']}")
            print("-" * 60)

        print(f"\nSYSTEM RESERVE: {SYSTEM_ACCOUNT}")

        conn.commit()

        print("\n✅ OMEGA GENESIS COMPLETE")
        print("🔒 CANONICAL ACCOUNTS FROZEN")

    except Exception as e:
        conn.rollback()

        print("\n❌ ROLLED BACK")
        print(str(e))

    finally:
        conn.close()


if __name__ == "__main__":
    create_genesis()
