import sqlite3
import uuid
import sys

DB = "omega_ledger.db"

def create_account(user_id, initial_balance=0):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    account_id = str(uuid.uuid4())

    cur.execute("""
        INSERT INTO accounts (id, user_id, balance)
        VALUES (?, ?, ?)
    """, (account_id, user_id, initial_balance))

    conn.commit()
    conn.close()

    print(f"[ISSUED] {user_id} -> {account_id} -> {initial_balance}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python create_account.py USER_ID")
        exit()

    create_account(sys.argv[1])
