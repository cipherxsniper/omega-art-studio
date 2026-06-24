#!/usr/bin/env python3

import psycopg2
import uuid
import random
from datetime import datetime, UTC

DB_NAME = "omega_bank"
DB_USER = "omega"

TREASURY_WALLET = "2db2e016-f6a1-4086-bec2-363edfb1c26b"

def conn():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER
    )

def ensure_tables():
    c = conn()

    with c.cursor() as cur:

        cur.execute("""
        CREATE TABLE IF NOT EXISTS payment_authorizations (
            id UUID PRIMARY KEY,
            wallet_id UUID NOT NULL,
            merchant TEXT NOT NULL,
            amount NUMERIC(20,2) NOT NULL,
            status TEXT NOT NULL,
            network TEXT NOT NULL,
            response_code TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS payment_settlements (
            id UUID PRIMARY KEY,
            auth_id UUID NOT NULL,
            wallet_id UUID NOT NULL,
            merchant TEXT NOT NULL,
            amount NUMERIC(20,2) NOT NULL,
            status TEXT NOT NULL,
            settled_at TIMESTAMP NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS payment_reversals (
            id UUID PRIMARY KEY,
            auth_id UUID NOT NULL,
            wallet_id UUID NOT NULL,
            amount NUMERIC(20,2) NOT NULL,
            reason TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
        """)

    c.commit()
    c.close()

def get_balance(wallet_id):

    c = conn()

    with c.cursor() as cur:

        cur.execute("""
        SELECT settled_balance
        FROM wallets
        WHERE id = %s
        """, (wallet_id,))

        row = cur.fetchone()

    c.close()

    if not row:
        return 0

    return float(row[0])

def ledger_transfer(
    source_wallet,
    destination_wallet,
    amount,
    reference
):

    c = conn()

    try:

        with c.cursor() as cur:

            cur.execute("""
            UPDATE wallets
            SET settled_balance = settled_balance - %s
            WHERE id = %s
            """, (amount, source_wallet))

            cur.execute("""
            UPDATE wallets
            SET settled_balance = settled_balance + %s
            WHERE id = %s
            """, (amount, destination_wallet))

            cur.execute("""
            INSERT INTO ledger_entries (
                id,
                transaction_id,
                wallet_id,
                direction,
                amount,
                idempotency_key,
                created_at
            )
            VALUES (
                gen_random_uuid(),
                gen_random_uuid(),
                %s,
                'DEBIT',
                %s,
                %s,
                NOW()
            )
            """, (
                source_wallet,
                amount,
                reference + "-debit"
            ))

            cur.execute("""
            INSERT INTO ledger_entries (
                id,
                transaction_id,
                wallet_id,
                direction,
                amount,
                idempotency_key,
                created_at
            )
            VALUES (
                gen_random_uuid(),
                gen_random_uuid(),
                %s,
                'CREDIT',
                %s,
                %s,
                NOW()
            )
            """, (
                destination_wallet,
                amount,
                reference + "-credit"
            ))

        c.commit()

        return {
            "status": "OK"
        }

    except Exception as e:

        c.rollback()

        return {
            "status": "ERROR",
            "error": str(e)
        }

    finally:
        c.close()

def authorize_transaction(
    wallet_id,
    merchant,
    amount
):

    auth_id = str(uuid.uuid4())

    balance = get_balance(wallet_id)

    network = random.choice([
        "VISA",
        "MASTERCARD"
    ])

    if balance < amount:

        response_code = "51"

        status = "DECLINED"

    else:

        response_code = "00"

        status = "AUTHORIZED"

    c = conn()

    with c.cursor() as cur:

        cur.execute("""
        INSERT INTO payment_authorizations (
            id,
            wallet_id,
            merchant,
            amount,
            status,
            network,
            response_code,
            created_at
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            auth_id,
            wallet_id,
            merchant,
            amount,
            status,
            network,
            response_code,
            datetime.now(UTC)
        ))

    c.commit()
    c.close()

    return {
        "auth_id": auth_id,
        "wallet_id": wallet_id,
        "merchant": merchant,
        "amount": amount,
        "network": network,
        "response_code": response_code,
        "status": status
    }

def settle_transaction(auth_id):

    c = conn()

    with c.cursor() as cur:

        cur.execute("""
        SELECT
            wallet_id,
            merchant,
            amount,
            status
        FROM payment_authorizations
        WHERE id = %s
        """, (auth_id,))

        row = cur.fetchone()

    c.close()

    if not row:

        return {
            "status": "ERROR",
            "error": "AUTH_NOT_FOUND"
        }

    wallet_id = row[0]
    merchant = row[1]
    amount = float(row[2])
    status = row[3]

    if status != "AUTHORIZED":

        return {
            "status": "ERROR",
            "error": "AUTH_NOT_APPROVED"
        }

    transfer = ledger_transfer(
        wallet_id,
        TREASURY_WALLET,
        amount,
        "settlement-" + auth_id
    )

    if transfer["status"] != "OK":
        return transfer

    settlement_id = str(uuid.uuid4())

    c = conn()

    with c.cursor() as cur:

        cur.execute("""
        INSERT INTO payment_settlements (
            id,
            auth_id,
            wallet_id,
            merchant,
            amount,
            status,
            settled_at
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            settlement_id,
            auth_id,
            wallet_id,
            merchant,
            amount,
            "SETTLED",
            datetime.now(UTC)
        ))

    c.commit()
    c.close()

    return {
        "status": "SETTLED",
        "settlement_id": settlement_id,
        "auth_id": auth_id,
        "amount": amount
    }

def reverse_transaction(auth_id, reason):

    c = conn()

    with c.cursor() as cur:

        cur.execute("""
        SELECT
            wallet_id,
            amount
        FROM payment_authorizations
        WHERE id = %s
        """, (auth_id,))

        row = cur.fetchone()

    c.close()

    if not row:

        return {
            "status": "ERROR",
            "error": "AUTH_NOT_FOUND"
        }

    wallet_id = row[0]
    amount = float(row[1])

    transfer = ledger_transfer(
        TREASURY_WALLET,
        wallet_id,
        amount,
        "reversal-" + auth_id
    )

    if transfer["status"] != "OK":
        return transfer

    reversal_id = str(uuid.uuid4())

    c = conn()

    with c.cursor() as cur:

        cur.execute("""
        INSERT INTO payment_reversals (
            id,
            auth_id,
            wallet_id,
            amount,
            reason,
            created_at
        )
        VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            reversal_id,
            auth_id,
            wallet_id,
            amount,
            reason,
            datetime.now(UTC)
        ))

    c.commit()
    c.close()

    return {
        "status": "REVERSED",
        "reversal_id": reversal_id,
        "amount": amount
    }

def run_demo():

    ensure_tables()

    wallet_id = "fe881e17-8b24-42f4-ba4f-c1ce38770b51"

    print("\n=== AUTHORIZATION ===\n")

    auth = authorize_transaction(
        wallet_id,
        "OMEGA_NETWORK_STORE",
        375.25
    )

    print(auth)

    if auth["status"] != "AUTHORIZED":
        return

    print("\n=== SETTLEMENT ===\n")

    settlement = settle_transaction(
        auth["auth_id"]
    )

    print(settlement)

    print("\n=== REVERSAL ===\n")

    reversal = reverse_transaction(
        auth["auth_id"],
        "CUSTOMER_REFUND"
    )

    print(reversal)

if __name__ == "__main__":
    run_demo()

