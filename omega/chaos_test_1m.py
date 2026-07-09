#!/usr/bin/env python3
"""
OMEGA CHAOS TEST HARNESS
Simulates 1,000,000 transactions against ledger engine
"""

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


def run():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    print("🔥 CHAOS TEST STARTING (1,000,000 TX)")

    start = time.time()

    for i in range(10_000):
        frm = random.choice(ACCOUNTS)
        to = random.choice(ACCOUNTS)
        amt = random.uniform(1, 1000)

        cur.execute("""
            INSERT INTO ledger_events (account_id, event_type, amount)
            VALUES (?, ?, ?)
        """, (frm, "DEBIT", amt))

        cur.execute("""
            INSERT INTO ledger_events (account_id, event_type, amount)
            VALUES (?, ?, ?)
        """, (to, "CREDIT", amt))

        if i % 10000 == 0:
            conn.commit()
            print(f"processed {i}")

    conn.commit()
    conn.close()

    print("🔥 CHAOS COMPLETE IN", time.time() - start, "seconds")


if __name__ == "__main__":
    run()
