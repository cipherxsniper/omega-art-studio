import psycopg2
import uuid
from datetime import datetime

def execute_transaction(from_wallet, to_wallet, amount, idem_key):
    conn = psycopg2.connect(dbname="omega_bank", user="omega")

    try:
        with conn.cursor() as cur:

            # 1. IDEMPOTENCY
            cur.execute("""
                SELECT 1 FROM ledger_entries
                WHERE idempotency_key = %s
            """, (idem_key,))

            if cur.fetchone():
                conn.rollback()
                return {"status": "DUPLICATE_IGNORED"}

            # 2. LOCK BOTH WALLETS
            cur.execute("""
                SELECT id, settled_balance FROM wallets
                WHERE id IN (%s, %s)
                FOR UPDATE
            """, (from_wallet, to_wallet))

            rows = cur.fetchall()
            if len(rows) != 2:
                conn.rollback()
                return {"status": "WALLET_NOT_FOUND"}

            # 3. CHECK FUNDS
            cur.execute("""
                SELECT settled_balance FROM wallets WHERE id=%s
            """, (from_wallet,))
            balance = cur.fetchone()[0]

            if balance < amount:
                conn.rollback()
                return {"status": "INSUFFICIENT_FUNDS"}

            # 4. APPLY BALANCES
            cur.execute("""
                UPDATE wallets
                SET settled_balance = settled_balance - %s
                WHERE id = %s
            """, (amount, from_wallet))

            cur.execute("""
                UPDATE wallets
                SET settled_balance = settled_balance + %s
                WHERE id = %s
            """, (amount, to_wallet))

            # 5. DOUBLE ENTRY LEDGER (CRITICAL FIX)
            tx_id = str(uuid.uuid4())

            cur.execute("""
                INSERT INTO ledger_entries (
                    id, transaction_id, wallet_id, direction, amount, idempotency_key, created_at
                ) VALUES (%s,%s,%s,'DEBIT',%s,%s,%s)
            """, (
                str(uuid.uuid4()),
                tx_id,
                from_wallet,
                amount,
                idem_key,
                datetime.utcnow()
            ))

            cur.execute("""
                INSERT INTO ledger_entries (
                    id, transaction_id, wallet_id, direction, amount, idempotency_key, created_at
                ) VALUES (%s,%s,%s,'CREDIT',%s,%s,%s)
            """, (
                str(uuid.uuid4()),
                tx_id,
                to_wallet,
                amount,
                idem_key,
                datetime.utcnow()
            ))

        conn.commit()
        return {"status": "SETTLED", "tx_id": tx_id}

    except Exception as e:
        conn.rollback()
        return {"status": "ERROR", "error": str(e)}

    finally:
        conn.close()
