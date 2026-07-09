import uuid
from decimal import Decimal
from datetime import datetime, UTC

import psycopg2
import psycopg2.extras

from omega_institutional_accounts_v2 import INSTITUTIONAL_ACCOUNTS

DB_NAME = "omega_bank"
DB_USER = "omega"


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


def append_event(cur, event):

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
            Decimal(event["amount"]),
            event["currency"],
            event["version"]
        )
    )


def append_posting(
    cur,
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
            str(uuid.uuid4()),
            event_id,
            sequence_number,
            account_type,
            account_id,
            direction,
            Decimal(amount),
            currency
        )
    )


def issue_account(conn, semantic_key, acct):

    cur = conn.cursor()

    event_id = str(uuid.uuid4())

    amount = acct["target_balance"]

    issuance_amount = abs(amount)

    event = {
        "event_id": event_id,
        "event_type": "GENESIS_ISSUED_V2",
        "aggregate_id": acct["account_id"],
        "aggregate_type": acct["account_type"],
        "timestamp": datetime.now(UTC).isoformat(),
        "merchant_id": "omega_genesis_v2",
        "wallet_id": acct["account_id"],
        "amount": str(issuance_amount),
        "currency": "USD",
        "payload": {
            "semantic_key": semantic_key,
            "issuance_version": 2,
            "reserve_backed": True
        },
        "version": 2
    }

    append_event(cur, event)

    seq = next_sequence(cur)

    reserve = INSTITUTIONAL_ACCOUNTS["RESERVE"]

    # RESERVE DEBIT
    append_posting(
        cur=cur,
        event_id=event_id,
        sequence_number=seq,
        account_type=reserve["account_type"],
        account_id=reserve["account_id"],
        direction="DEBIT",
        amount=issuance_amount,
        currency="USD"
    )

    seq += 1

    # INSTITUTIONAL CREDIT
    append_posting(
        cur=cur,
        event_id=event_id,
        sequence_number=seq,
        account_type=acct["account_type"],
        account_id=acct["account_id"],
        direction="CREDIT",
        amount=issuance_amount,
        currency="USD"
    )

    print(f"✅ ISSUED: {semantic_key}")


def run():

    conn = connect()

    try:

        conn.autocommit = False

        for semantic_key, acct in INSTITUTIONAL_ACCOUNTS.items():

            if semantic_key == "RESERVE":
                continue

            issue_account(conn, semantic_key, acct)

        conn.commit()

        print("\n🏦 OMEGA GENESIS ISSUANCE v2 COMPLETE")
        print("🔒 RESERVE-BACKED CAPITALIZATION FROZEN")

    except Exception as e:

        conn.rollback()

        print("❌ ROLLED BACK")
        print(str(e))

    finally:

        conn.close()


if __name__ == "__main__":
    run()

