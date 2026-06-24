from omega_db_kernel_v1 import OmegaTransaction

def view_balances():
    with OmegaTransaction() as cur:
        cur.execute("""
            SELECT
                account_id,
                account_type,
                SUM(
                    CASE
                        WHEN direction = 'CREDIT' THEN amount
                        ELSE -amount
                    END
                ) AS balance
            FROM ledger_postings
            GROUP BY account_id, account_type
            ORDER BY balance DESC;
        """)
        return cur.fetchall()


def print_balances():
    rows = view_balances()

    print("🏦 OMEGA BALANCE VIEW (CANONICAL)")
    print("=" * 60)

    for r in rows:
        print(f"{r['account_type']:<12} {r['account_id']}  {r['balance']}")

    print("=" * 60)


if __name__ == "__main__":
    print_balances()
