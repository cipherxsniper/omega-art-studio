#!/usr/bin/env python3

import time
import psycopg2

# assumes these already exist in your system:
# clear(), header(), safe_query()

def run():
    conn = psycopg2.connect(dbname="omega_bank", user="omega")

    while True:
        try:
            clear()
            header()

            wallets = safe_query(conn, """
                SELECT id, settled_balance
                FROM wallets
                ORDER BY settled_balance DESC
                LIMIT 10
            """)

            drift = safe_query(conn, """
                SELECT wallet_id, drift
                FROM obs_wallet_health
                ORDER BY ABS(drift) DESC
                LIMIT 10
            """)

            queue = safe_query(conn, """
                SELECT status, COUNT(*)
                FROM settlement_queue
                GROUP BY status
            """)

            risk = safe_query(conn, """
                SELECT event_type, status, created_at
                FROM invariant_failures
                ORDER BY created_at DESC
                LIMIT 5
            """)

            print("\n[WALLETS]")
            print(wallets)

            print("\n[DRIFT]")
            print(drift)

            print("\n[QUEUE]")
            print(queue)

            print("\n[RISK]")
            print(risk)

            time.sleep(2)

        except Exception as e:
            # CRITICAL: recover from aborted transactions
            try:
                conn.rollback()
            except:
                pass

            print("[UI RECOVERABLE ERROR]", e)
            time.sleep(2)


if __name__ == "__main__":
    run()
