
import uuid
from decimal import Decimal
from datetime import datetime, UTC

import psycopg2
import psycopg2.extras

DB_NAME = "omega_bank"
DB_USER = "omega"

# ─────────────────────────────────────────────
# CANONICAL CAPITAL CONFIG (FROZEN STATE)
# ─────────────────────────────────────────────

CAPITAL_ACCOUNTS = [
    {
        "name": "OMEGA_TREASURY",
        "type": "TREASURY",
        "id": "acd27fe4-1862-48ff-a343-5595cc7ca49b",
        "amount": Decimal("12500000000.00")
    },
    {
        "name": "THOMAS_LEE_HARVEY",
        "type": "FOUNDER",
        "id": "7fb91891-2f60-4edb-8600-e9c42c4ac33c",
        "amount": Decimal("50000000.00")
    },
    {
        "name": "OMEGA_CREDIT",
        "type": "CREDIT",
        "id": "a74c8ad9-06c3-42ba-b4c2-a3b62a493106",
        "amount": Decimal("250000000.00")
    },
    {
        "name": "OMEGA_INVESTMENT",
        "type": "INVESTMENT",
        "id": "823a17d1-2846-4006-a631-ba48f9a88de4",
        "amount": Decimal("500000000.00")
    },
    {
        "name": "OMEGA_SYSTEM_RESERVE",
        "type": "SYSTEM",
        "id": "99238820-7da1-4afd-93f5-c37fa6ad669b",
        "amount": Decimal("-13300000000.00")
    }
]

GENESIS_FLAG = "OMEGA_CAPITAL_FROZEN_V1"


# ─────────────────────────────────────────────
# DB CONNECT
# ─────────────────────────────────────────────

def connect():
    return psycopg2.connect(
        database=DB_NAME,
        user=DB_USER
    )


# ─────────────────────────────────────────────
# IDENTITY CHECK (IDEMPOTENCY GUARD)
# ─────────────────────────────────────────────

def already_frozen(cur):

    cur.execute("""
        SELECT COUNT(*)
        FROM omega_events
        WHERE event_type = %s
    """, (GENESIS_FLAG,))

    return cur.fetchone()[0] > 0


# ─────────────────────────────────────────────
# EVENT WRITER
# ─────────────────────────────────────────────

def write_event(cur, account):

    event_id = str(uuid.uuid4())

    cur.execute("""
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
        VALUES (%s,%s,%s,%s,%s,NOW(),%s,%s,%s,%s,%s,%s)
    """, (
        event_id,
        GENESIS_FLAG,
        account["id"],
        account["type"],
        psycopg2.extras.Json({
            "name": account["name"],
            "capital_frozen": True
        }),
        datetime.now(UTC).isoformat(),
        "omega_system",
        account["id"],
        str(account["amount"]),
        "USD",
        1
    ))

    return event_id


# ─────────────────────────────────────────────
# POSTING WRITER (DOUBLE ENTRY)
# ─────────────────────────────────────────────

def write_postings(cur, event_id, account):

    # system counter-entry (conceptual ledger closure)
    cur.execute("""
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
        SELECT
            %s,%s,
            COALESCE(MAX(sequence_number),0)+1,
            'SYSTEM',
            '99238820-7da1-4afd-93f5-c37fa6ad669b',
            'DEBIT',
            %s,
            'USD'
        FROM ledger_postings
    """, (
        str(uuid.uuid4()),
        event_id,
        abs(account["amount"])
    ))

    # institutional account entry
    cur.execute("""
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
        SELECT
            %s,%s,
            COALESCE(MAX(sequence_number),0)+2,
            %s,
            %s,
            'CREDIT',
            %s,
            'USD'
        FROM ledger_postings
    """, (
        str(uuid.uuid4()),
        event_id,
        account["type"],
        account["id"],
        abs(account["amount"])
    ))


# ─────────────────────────────────────────────
# MAIN FREEZE ENGINE
# ─────────────────────────────────────────────

def freeze_capital():

    conn = connect()
    cur = conn.cursor()

    try:

        conn.autocommit = False

        # 🔒 IDENTITY GUARD
        if already_frozen(cur):
            print("🛑 CAPITAL ALREADY FROZEN — EXIT SAFE")
            return

        print("🏦 OMEGA CAPITAL FREEZE v1 STARTING")

        for acct in CAPITAL_ACCOUNTS:

            print(f"💰 Issuing: {acct['name']}")

            event_id = write_event(cur, acct)

            write_postings(cur, event_id, acct)

        conn.commit()

        print("\n🔒 CAPITAL FREEZE COMPLETE")
        print("📌 ALL INSTITUTIONAL ACCOUNTS LOCKED")
        print("📌 GENESIS IS IMMUTABLE")

    except Exception as e:

        conn.rollback()

        print("❌ CAPITAL FREEZE FAILED")
        print(str(e))

    finally:

        conn.close()


# ─────────────────────────────────────────────
# ENTRY
# ─────────────────────────────────────────────

if __name__ == "__main__":
    freeze_capital()

