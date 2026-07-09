import sqlite3

DB_PATH = "omega_ledger.db"

def rebuild():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # reset projection table
    cur.execute("DROP TABLE IF EXISTS accounts")

    cur.execute("""
        CREATE TABLE accounts (
            account_id TEXT PRIMARY KEY,
            balance REAL DEFAULT 0
        )
    """)

    # rebuild from events
    cur.execute("""
        SELECT account_id, event_type, amount
        FROM ledger_events
    """)

    rows = cur.fetchall()

    balances = {}

    for account_id, event_type, amount in rows:
        if account_id not in balances:
            balances[account_id] = 0.0

        if event_type == "CREDIT":
            balances[account_id] += amount
        elif event_type == "DEBIT":
            balances[account_id] -= amount

    for acc, bal in balances.items():
        cur.execute("""
            INSERT INTO accounts (account_id, balance)
            VALUES (?, ?)
        """, (acc, bal))

    conn.commit()

    total = sum(balances.values())

    print("🏦 REBUILD COMPLETE")
    print(f"Accounts: {len(balances)}")
    print(f"TOTAL LEDGER VALUE: ${total:,.2f} USD")

if __name__ == "__main__":
    rebuild()
