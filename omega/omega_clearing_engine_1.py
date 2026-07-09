from datetime import datetime, timedelta

def build_clearing_batch(conn):
    with conn.cursor() as cur:

        now = datetime.utcnow()
        window_start = now - timedelta(minutes=5)

        # 1. CREATE BATCH
        cur.execute("""
            INSERT INTO clearing_batches (
                status,
                window_start,
                window_end
            )
            VALUES ('OPEN', %s, %s)
            RETURNING id;
        """, (window_start, now))

        batch_id = cur.fetchone()[0]

        # 2. COLLECT CAPTURED TRANSACTIONS
        cur.execute("""
            SELECT id, wallet_id, amount
            FROM ledger_entries
            WHERE created_at BETWEEN %s AND %s;
        """, (window_start, now))

        rows = cur.fetchall()

        # 3. INSERT INTO CLEARING POOL
        for tx_id, wallet_id, amount in rows:
            cur.execute("""
                INSERT INTO clearing_items (
                    batch_id,
                    wallet_id,
                    amount,
                    direction,
                    transaction_id,
                    status
                )
                VALUES (%s, %s, %s, 'DEBIT', %s, 'PENDING');
            """, (batch_id, wallet_id, amount, tx_id))

        conn.commit()

        return {"batch_id": str(batch_id), "items": len(rows)}

def settle_batch(conn, batch_id):
    with conn.cursor() as cur:

        # 1. GET ALL ITEMS
        cur.execute("""
            SELECT wallet_id, SUM(amount)
            FROM clearing_items
            WHERE batch_id = %s
            GROUP BY wallet_id;
        """, (batch_id,))

        totals = cur.fetchall()

        # 2. APPLY NET SETTLEMENT
        for wallet_id, net_amount in totals:

            cur.execute("""
                UPDATE wallets
                SET settled_balance = settled_balance - %s
                WHERE id = %s;
            """, (net_amount, wallet_id))

        # 3. CLOSE BATCH
        cur.execute("""
            UPDATE clearing_batches
            SET status = 'SETTLED'
            WHERE id = %s;
        """, (batch_id,))

        conn.commit()

        return {"status": "SETTLED", "batch_id": batch_id}
