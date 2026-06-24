import sqlite3
import uuid
import random
import time

DB = "omega_ledger.db"

def gen_acct():
    return "ACCT-" + uuid.uuid4().hex[:10].upper()

def gen_route():
    return "RT-" + uuid.uuid4().hex[:12]

def gen_wallet():
    return "0x" + uuid.uuid4().hex

def run():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT id FROM accounts")
    accounts = cur.fetchall()

    for (acct_id,) in accounts:
        cur.execute("""
            UPDATE accounts
            SET account_number=?,
                routing_number=?,
                wallet_addr=?
            WHERE id=?
        """, (
            gen_acct(),
            gen_route(),
            gen_wallet(),
            acct_id
        ))

        cur.execute("""
            INSERT INTO ledger_events (event_id, event_type, payload, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            "WALLET_GENESIS",
            acct_id,
            time.time()
        ))

    conn.commit()
    conn.close()
    print("[GENESIS LINK COMPLETE] accounts fully issued")

if __name__ == "__main__":
    run()
