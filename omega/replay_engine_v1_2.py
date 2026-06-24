#!/usr/bin/env python3

import psycopg2
import json
from decimal import Decimal

DB_NAME = "omega_bank"
DB_USER = "omega"

def db():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER
    )

def ensure_projection_tables(cur):

    cur.execute("""
        CREATE TABLE IF NOT EXISTS wallet_state_projection (
            wallet_id UUID PRIMARY KEY,
            available_balance NUMERIC(20,2) DEFAULT 0,
            reserved_balance NUMERIC(20,2) DEFAULT 0,
            settled_balance NUMERIC(20,2) DEFAULT 0,
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS treasury_state_projection (
            treasury_id UUID PRIMARY KEY,
            reserve_balance NUMERIC(20,2) DEFAULT 0,
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """)

def wipe_projections(cur):

    cur.execute("DELETE FROM wallet_state_projection;")
    cur.execute("DELETE FROM treasury_state_projection;")

def ensure_wallet(cur, wallet_id):

    cur.execute("""
        INSERT INTO wallet_state_projection (
            wallet_id,
            available_balance,
            reserved_balance,
            settled_balance
        )
        VALUES (%s,0,0,0)
        ON CONFLICT (wallet_id) DO NOTHING;
    """, (wallet_id,))

def ensure_treasury(cur, treasury_id):

    cur.execute("""
        INSERT INTO treasury_state_projection (
            treasury_id,
            reserve_balance
        )
        VALUES (%s,0)
        ON CONFLICT (treasury_id) DO NOTHING;
    """, (treasury_id,))

def apply_wallet_delta(
    cur,
    wallet_id,
    available_delta=0,
    reserved_delta=0,
    settled_delta=0
):

    ensure_wallet(cur, wallet_id)

    cur.execute("""
        UPDATE wallet_state_projection
        SET
            available_balance = available_balance + %s,
            reserved_balance = reserved_balance + %s,
            settled_balance = settled_balance + %s,
            updated_at = NOW()
        WHERE wallet_id = %s
    """, (
        Decimal(str(available_delta)),
        Decimal(str(reserved_delta)),
        Decimal(str(settled_delta)),
        wallet_id
    ))

def apply_treasury_delta(
    cur,
    treasury_id,
    reserve_delta=0
):

    ensure_treasury(cur, treasury_id)

    cur.execute("""
        UPDATE treasury_state_projection
        SET
            reserve_balance = reserve_balance + %s,
            updated_at = NOW()
        WHERE treasury_id = %s
    """, (
        Decimal(str(reserve_delta)),
        treasury_id
    ))

def replay():

    conn = db()
    cur = conn.cursor()

    ensure_projection_tables(cur)

    print("WIPING PROJECTIONS...")
    wipe_projections(cur)

    cur.execute("""
        SELECT
            id,
            event_type,
            aggregate_type,
            aggregate_id,
            payload,
            created_at
        FROM ledger_events
        ORDER BY created_at ASC
    """)

    rows = cur.fetchall()

    print(f"REPLAYING {len(rows)} EVENTS...\n")

    for row in rows:

        event_id = str(row[0])
        event_type = row[1]
        aggregate_type = row[2]
        aggregate_id = str(row[3])
        payload = row[4]

        if isinstance(payload, str):
            payload = json.loads(payload)

        print(f"APPLYING: {event_type}")

        if event_type == "ACH_SETTLEMENT_POSTED":

            amount = Decimal(str(payload["amount"]))

            apply_wallet_delta(
                cur,
                aggregate_id,
                available_delta=amount,
                settled_delta=amount
            )

        elif event_type == "ISSUER_AUTH_APPROVED":

            amount = Decimal(str(payload["amount"]))

            apply_wallet_delta(
                cur,
                aggregate_id,
                available_delta=-amount,
                reserved_delta=amount
            )

        elif event_type == "SETTLEMENT_POSTED":

            amount = Decimal(str(payload["amount"]))

            apply_wallet_delta(
                cur,
                aggregate_id,
                reserved_delta=-amount
            )

        elif event_type == "CUSTODY_RESERVE_SYNC":

            reserve_balance = Decimal(
                str(payload["reserve_balance"])
            )

            ensure_treasury(cur, aggregate_id)

            cur.execute("""
                UPDATE treasury_state_projection
                SET
                    reserve_balance = %s,
                    updated_at = NOW()
                WHERE treasury_id = %s
            """, (
                reserve_balance,
                aggregate_id
            ))

    conn.commit()

    print("\nREPLAY COMPLETE\n")

    print("=== WALLET STATE ===")

    cur.execute("""
        SELECT
            wallet_id,
            available_balance,
            reserved_balance,
            settled_balance
        FROM wallet_state_projection
    """)

    for row in cur.fetchall():
        print(row)

    print("\n=== TREASURY STATE ===")

    cur.execute("""
        SELECT
            treasury_id,
            reserve_balance
        FROM treasury_state_projection
    """)

    for row in cur.fetchall():
        print(row)

    cur.close()
    conn.close()

if __name__ == "__main__":
    replay()

