import psycopg2
import json

DB = "dbname=omega_bank user=omega"

def run():
    conn = psycopg2.connect(DB)
    cur = conn.cursor()

    # ledger truth
    cur.execute("""
        SELECT wallet_id,
               SUM(CASE WHEN direction='CREDIT' THEN amount ELSE -amount END)
        FROM ledger_entries
        GROUP BY wallet_id;
    """)

    ledger = {w: float(v) for w, v in cur.fetchall()}

    # IMPORTANT: correct table is wallet_state
    cur.execute("""
        SELECT wallet_id, settled_balance
        FROM wallet_state;
    """)

    wallets = {w: float(v) for w, v in cur.fetchall()}

    drift = {}

    for w in wallets:
        l = ledger.get(w, 0)
        s = wallets[w]
        if abs(l - s) > 0.01:
            drift[w] = {
                "ledger": l,
                "wallet": s,
                "delta": l - s
            }

    print(json.dumps({
        "ledger": ledger,
        "wallets": wallets,
        "drift": drift
    }, indent=2))

if __name__ == "__main__":
    run()
