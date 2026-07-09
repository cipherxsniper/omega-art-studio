#!/usr/bin/env python3

from contextlib import contextmanager

def check_invariants(conn):
    with conn.cursor() as cur:

        cur.execute("""
            SELECT w.id,
                   w.settled_balance,
                   COALESCE(SUM(
                       CASE WHEN le.direction='CREDIT' THEN le.amount
                       ELSE -le.amount END
                   ),0)
            FROM wallets w
            LEFT JOIN ledger_entries le ON w.id = le.wallet_id
            GROUP BY w.id, w.settled_balance
        """)

        rows = cur.fetchall()

        for wallet_id, wallet_balance, ledger_balance in rows:
            if float(wallet_balance) != float(ledger_balance):
                cur.execute("""
                    INSERT INTO invariant_failures
                    (id, invariant_name, failure_details, severity)
                    VALUES (gen_random_uuid(),
                            'WALLET_LEDGER_DRIFT',
                            %s,
                            'CRITICAL')
                """, (
                    f"wallet={wallet_id} wallet_balance={wallet_balance} ledger_balance={ledger_balance}",
                ))

                conn.commit()

                raise Exception("INVARIANT FAILURE BLOCKED EXECUTION")

    return True


@contextmanager
def invariant_guard(conn):
    check_invariants(conn)
    yield
    check_invariants(conn)
