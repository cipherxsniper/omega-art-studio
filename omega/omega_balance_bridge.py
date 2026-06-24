import psycopg2

DB = "omega_bank"
USER = "omega"

def get_real_balances():
    conn = psycopg2.connect(dbname=DB, user=USER)

    with conn.cursor() as cur:
        cur.execute("""
            SELECT wallet_id,
                   settled_balance,
                   ledger_balance,
                   drift
            FROM obs_wallet_health
            ORDER BY settled_balance DESC;
        """)

        rows = cur.fetchall()
        conn.close()
        return rows
