import time
from omega_risk_engine import compute_risk
from omega_policy_engine import decide
from omega_treasury_coordinator import apply_policy
import psycopg2

def conn():
    return psycopg2.connect(dbname="omega_bank", user="omega")

def get_wallet_limit(cur, wallet_id):
    cur.execute("SELECT current_limit FROM credit_policy_state WHERE wallet_id=%s", (wallet_id,))
    row = cur.fetchone()
    return row[0] if row else 0

def fetch_transactions(cur):
    cur.execute("""
        SELECT wallet_id, amount, merchant_risk, velocity_1m
        FROM transaction_stream
        ORDER BY created_at DESC
        LIMIT 50
    """)
    return cur.fetchall()

def run_engine():
    c = conn()

    while True:
        try:
            cur = c.cursor()
            events = fetch_transactions(cur)

            for e in events:
                tx = {
                    "wallet_id": e[0],
                    "amount": float(e[1]),
                    "merchant_risk": float(e[2]),
                    "velocity_1m": float(e[3])
                }

                risk = compute_risk(tx)
                current_limit = get_wallet_limit(cur, tx["wallet_id"])

                state, new_limit = decide(risk, current_limit)

                apply_policy(tx["wallet_id"], state, new_limit)

            c.commit()
            time.sleep(1)

        except Exception as e:
            c.rollback()
            print("[RISK LOOP ERROR]", e)
            time.sleep(2)

if __name__ == "__main__":
    run_engine()
