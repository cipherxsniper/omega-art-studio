#!/usr/bin/env python3

import psycopg2
import uuid
from datetime import datetime, UTC

DB = "omega_bank"
USER = "omega"

SYSTEM_WALLET = "2db2e016-f6a1-4086-bec2-363edfb1c26b"

def conn():
    return psycopg2.connect(
        dbname=DB,
        user=USER
    )

def authorize(wallet_id, amount, merchant):

    c = conn()

    try:

        txid = str(uuid.uuid4())

        idem_debit = f"{txid}-debit"
        idem_credit = f"{txid}-credit"

        with c.cursor() as cur:

            cur.execute("""
                SELECT settled_balance
                FROM wallets
                WHERE id = %s
                FOR UPDATE
            """, (wallet_id,))

            row = cur.fetchone()

            if not row:
                return {"status": "WALLET_NOT_FOUND"}

            balance = float(row[0])

            if balance < amount:
                return {
                    "status": "DECLINED",
                    "reason": "INSUFFICIENT_FUNDS",
                    "balance": balance
                }

            # -----------------------------
            # DOUBLE ENTRY LEDGER WRITES
            # -----------------------------

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
                VALUES
                (
                    gen_random_uuid(),
                    %s,
                    %s,
                    'DEBIT',
                    %s,
                    %s,
                    NOW()
                ),
                (
                    gen_random_uuid(),
                    %s,
                    %s,
                    'CREDIT',
                    %s,
                    %s,
                    NOW()
                )
            """, (
                txid,
                wallet_id,
                amount,
                idem_debit,

                txid,
                SYSTEM_WALLET,
                amount,
                idem_credit
            ))

            # -----------------------------
            # WALLET BALANCE UPDATES
            # -----------------------------

            cur.execute("""
                UPDATE wallets
                SET settled_balance = settled_balance - %s
                WHERE id = %s
            """, (amount, wallet_id))

            cur.execute("""
                UPDATE wallets
                SET settled_balance = settled_balance + %s
                WHERE id = %s
            """, (amount, SYSTEM_WALLET))

        c.commit()

        return {
            "status": "AUTHORIZED",
            "transaction_id": txid,
            "merchant": merchant,
            "amount": amount,
            "timestamp": str(datetime.now(UTC))
        }

    except Exception as e:
        c.rollback()

        return {
            "status": "ERROR",
            "error": str(e)
        }

    finally:
        c.close()

if __name__ == "__main__":

    WALLET = "fe881e17-8b24-42f4-ba4f-c1ce38770b51"

    result = authorize(
        WALLET,
        250.75,
        "OMEGA_STORE"
    )

    print(result)
