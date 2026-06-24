import sqlite3
import sys
from account_registry import resolve_account

DB = "omega_ledger.db"

def transfer(frm, to, amount):
    frm = resolve_account(frm)
    to = resolve_account(to)
    amount = float(amount)

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # ensure accounts exist
    cur.execute("SELECT balance FROM accounts WHERE user_id=?", (frm,))
    f = cur.fetchone()
    if not f:
        print("[ERROR] FROM ACCOUNT NOT FOUND")
        return

    cur.execute("SELECT balance FROM accounts WHERE user_id=?", (to,))
    t = cur.fetchone()
    if not t:
        print("[ERROR] TO ACCOUNT NOT FOUND")
        return

    # balance update
    cur.execute("UPDATE accounts SET balance = balance - ? WHERE user_id=?", (amount, frm))
    cur.execute("UPDATE accounts SET balance = balance + ? WHERE user_id=?", (amount, to))

    conn.commit()

    print(f"[TRANSFER COMPLETE] {frm} → {to} : {amount}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("usage: python transfer.py FROM TO AMOUNT")
        sys.exit(1)

    transfer(sys.argv[1], sys.argv[2], sys.argv[3])
