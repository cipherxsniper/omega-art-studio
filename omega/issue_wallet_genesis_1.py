import sqlite3
import hashlib
import uuid
import time

DB = "omega_ledger.db"

FUNDED_ACCOUNTS = [
    "OMEGA_TREASURY",
    "OMEGA_CREDIT",
    "OMEGA_RESERVE",
    "OMEGA_INVESTMENT",
    "THOMAS_LH"
]

def ensure_column(cur, table, column, definition):
    cur.execute(f"PRAGMA table_info({table})")
    cols = [x[1] for x in cur.fetchall()]

    if column not in cols:
        cur.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )

def make_account_number(user):
    h = hashlib.sha256(user.encode()).hexdigest()[:12].upper()
    return f"ACCT-{h}"

def make_wallet(user):
    h = hashlib.sha256(
        f"{user}-{time.time()}".encode()
    ).hexdigest()
    return f"0x{h[:40]}"

def make_routing(user):
    h = hashlib.md5(user.encode()).hexdigest()[:9]
    return f"RT-{h}"

def ledger_event(cur, tx_type, amount, status):
    cur.execute("""
        INSERT INTO ledger (
            id,
            tx_type,
            amount,
            status
        ) VALUES (?, ?, ?, ?)
    """, (
        str(uuid.uuid4()),
        tx_type,
        amount,
        status
    ))

def run():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    ensure_column(cur, "accounts", "wallet_address", "TEXT")
    ensure_column(cur, "accounts", "routing_number", "TEXT")

    for user_id in FUNDED_ACCOUNTS:

        acct_num = make_account_number(user_id)
        wallet = make_wallet(user_id)
        routing = make_routing(user_id)

        cur.execute("""
            UPDATE accounts
            SET
                account_number=?,
                wallet_address=?,
                routing_number=?
            WHERE user_id=?
        """, (
            acct_num,
            wallet,
            routing,
            user_id
        ))

        ledger_event(
            cur,
            f"WALLET_GENESIS::{user_id}",
            0.0,
            "ISSUED"
        )

    conn.commit()
    conn.close()

    print("[WALLET GENESIS COMPLETE]")
    print("All funded accounts issued:")
    print("- account numbers")
    print("- routing numbers")
    print("- wallet addresses")
    print("- immutable ledger events")

if __name__ == "__main__":
    run()
