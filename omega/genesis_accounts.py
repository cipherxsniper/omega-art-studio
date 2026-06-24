import sqlite3
import time

DB = "omega_ledger.db"

GENESIS_ACCOUNTS = [
    ("SYSTEM", "SYSTEM"),
    ("REVENUE", "REVENUE"),
    ("TOMMY", "TOMMY_LH"),
    ("TREASURY", "OMEGA_TREASURY"),
    ("CREDIT", "OMEGA_CREDIT"),
    ("RESERVE", "OMEGA_RESERVE"),
    ("INVESTMENT", "OMEGA_INVESTMENT"),
]

def make_account_number(user_id):
    return f"Ω-{abs(hash(user_id)) % 10**10}"

def run():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    for label, user in GENESIS_ACCOUNTS:
        cur.execute("SELECT id FROM accounts WHERE user_id=?", (user,))
        row = cur.fetchone()

        account_number = make_account_number(user)

        if row:
            cur.execute(
                "UPDATE accounts SET account_number=? WHERE user_id=?",
                (account_number, user)
            )
        else:
            cur.execute(
                "INSERT INTO accounts (id, user_id, balance, account_number) VALUES (?, ?, ?, ?)",
                (user, user, 0.0, account_number)
            )

        # ledger record of genesis issuance
        cur.execute(
            "INSERT INTO ledger (id, tx_type, amount, status) VALUES (?, ?, ?, ?)",
            (f"genesis_{user}_{int(time.time())}", "GENESIS", 0.0, "ISSUED")
        )

    conn.commit()
    conn.close()

    print("[GENESIS COMPLETE] accounts minted + account numbers issued")

if __name__ == "__main__":
    run()
