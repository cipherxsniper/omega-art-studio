import sqlite3
import uuid
import time

DB = "omega_ledger.db"

ALLOCATIONS = {
    "OMEGA_RESERVE": 750000000.0,
    "OMEGA_CREDIT": 600000000.0,
    "OMEGA_INVESTMENT": 250000000.0,
    "THOMAS_LH": 50000000.0
}

TOTAL_CAPITALIZATION = 27000000000.0

def run():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    allocated = sum(ALLOCATIONS.values())
    treasury_remaining = TOTAL_CAPITALIZATION - allocated

    # treasury receives remaining capitalization
    final_allocations = dict(ALLOCATIONS)
    final_allocations["OMEGA_TREASURY"] = treasury_remaining

    tx_id = f"capitalization_{uuid.uuid4()}"

    for account, amount in final_allocations.items():

        # ensure account exists
        cur.execute(
            "SELECT user_id FROM accounts WHERE user_id=?",
            (account,)
        )

        if not cur.fetchone():
            cur.execute(
                """
                INSERT INTO accounts (
                    id,
                    user_id,
                    balance,
                    account_number
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    account,
                    account,
                    0.0,
                    f"Ω-{abs(hash(account)) % 10**10}"
                )
            )

        # balance mutation
        cur.execute(
            """
            UPDATE accounts
            SET balance = ?
            WHERE user_id = ?
            """,
            (amount, account)
        )

        # ledger issuance record
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
                f"{tx_id}_{account}",
                "CAPITALIZATION",
                amount,
                "SETTLED"
            )
        )

        # entries record
        cur.execute(
            """
            INSERT INTO entries (
                id,
                tx_id,
                account_id,
                type,
                amount,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                tx_id,
                account,
                "credit",
                amount,
                time.time()
            )
        )

    conn.commit()

    print("\n[CAPITALIZATION COMPLETE]")
    print(f"TOTAL SYSTEM CAPITALIZATION: ${TOTAL_CAPITALIZATION:,.2f}")

if __name__ == "__main__":
    run()
