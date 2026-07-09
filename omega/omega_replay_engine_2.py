import psycopg2

DB = {"dbname":"omega_bank","user":"omega"}

def replay(wallet_id):
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT event_type, payload
        FROM ledger_events
        WHERE aggregate_id = %s
        ORDER BY sequence_number ASC
    """, (wallet_id,))

    balance = 0

    for event_type, payload in cur.fetchall():
        amt = float(payload.get("amount", 0))

        if event_type in ("CREDIT", "HOLD_RELEASE"):
            balance += amt
        elif event_type in ("HOLD", "DEBIT"):
            balance -= amt

    conn.close()
    return balance

if __name__ == "__main__":
    import sys
    print("REPLAY_BALANCE:", replay(sys.argv[1]))
