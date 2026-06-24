import psycopg2

DB = "omega_bank"
USER = "omega"

def conn():
    return psycopg2.connect(dbname=DB, user=USER)

def apply_policy(wallet_id, state, limit):
    c = conn()
    with c.cursor() as cur:
        cur.execute("""
            INSERT INTO credit_policy_state
            (wallet_id, current_limit, state, last_updated)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (wallet_id)
            DO UPDATE SET
                current_limit = EXCLUDED.current_limit,
                state = EXCLUDED.state,
                last_updated = NOW()
        """, (wallet_id, limit, state))
    c.commit()
    c.close()
