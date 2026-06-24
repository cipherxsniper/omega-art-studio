import sqlite3
import random
import time

DB = "omega_ledger.db"

ACCOUNTS = [
    "OMEGA_TREASURY",
    "OMEGA_CREDIT",
    "OMEGA_RESERVE",
    "OMEGA_INVESTMENT",
    "THOMAS_LH"
]

def run(n=10000):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    print(f"🔥 CHAOS TEST START ({n} TX)")

    for i in range(n):
        frm = random.choice(ACCOUNTS)
        to = random.choice(ACCOUNTS)
        amt = random.uniform(1, 1000)

        cur.execute("""
            INSERT INTO ledger_events (account_id, event_type, amount, tx_id)
            VALUES (?, ?, ?, ?)
        """, (frm, "DEBIT", amt, f"TX-{i}"))

        cur.execute("""
            INSERT INTO ledger_events (account_id, event_type, amount, tx_id)
            VALUES (?, ?, ?, ?)
        """, (to, "CREDIT", amt, f"TX-{i}"))

        if i % 1000 == 0:
            conn.commit()
            print("processed", i)

    conn.commit()
    conn.close()

    print("🔥 CHAOS COMPLETE")

if __name__ == "__main__":
    run()
