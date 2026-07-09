import sqlite3
import uuid
import time

DB = "omega_ledger.db"

PROTECTED = {
    "OMEGA_TREASURY",
    "OMEGA_RESERVE",
    "OMEGA_CREDIT",
    "OMEGA_INVESTMENT",
    "THOMAS_LH",
}

def record_event(cur, tx_type, amount, status):
    cur.execute(
        """
        INSERT INTO ledger (
            id,
            tx_type,
            amount,
            status
        ) VALUES (?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            tx_type,
            amount,
            status
        )
    )

def run():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, user_id, balance
        FROM accounts
        WHERE balance = 0
    """)

    rows = cur.fetchall()

    deleted = 0

    for acc_id, user_id, balance in rows:

        if user_id in PROTECTED:
            continue

        # ledger audit event
        record_event(
            cur,
            f"ACCOUNT_PURGE::{user_id}",
            0.0,
            "DELETED"
        )

        # delete account
        cur.execute(
            "DELETE FROM accounts WHERE user_id=?",
            (user_id,)
        )

        deleted += 1

    # reconciliation ledger event
    record_event(
        cur,
        "ACCOUNT_RECONCILIATION",
        float(deleted),
        "COMPLETE"
    )

    conn.commit()
    conn.close()

    print(f"[PURGE COMPLETE] deleted={deleted}")

if __name__ == "__main__":
    run()
