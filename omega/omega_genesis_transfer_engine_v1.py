#!/usr/bin/env python3

from datetime import datetime, timezone


def transfer(conn, from_account, to_account, amount):
    cursor = conn.cursor()

    tx_id = f"GENESIS_TRANSFER_{int(datetime.now(timezone.utc).timestamp())}"
    timestamp = datetime.now(timezone.utc).timestamp()

    # ─────────────────────────────────────────────
    # DEBIT SOURCE ACCOUNT
    # ─────────────────────────────────────────────
    cursor.execute("""
        INSERT INTO ledger_events (
            account_id,
            event_type,
            amount,
            tx_id,
            timestamp
        ) VALUES (?, ?, ?, ?, ?)
    """, (
        from_account,
        "DEBIT",
        -amount,
        tx_id,
        timestamp
    ))

    # ─────────────────────────────────────────────
    # CREDIT DESTINATION ACCOUNT
    # ─────────────────────────────────────────────
    cursor.execute("""
        INSERT INTO ledger_events (
            account_id,
            event_type,
            amount,
            tx_id,
            timestamp
        ) VALUES (?, ?, ?, ?, ?)
    """, (
        to_account,
        "CREDIT",
        amount,
        tx_id,
        timestamp
    ))

    conn.commit()
    return tx_id


# ─────────────────────────────────────────────
# GENESIS TRANSFER EXECUTION (SAFE ENTRY POINT)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import sqlite3

    conn = sqlite3.connect("omega_bank.db")

    tx = transfer(
        conn,
        from_account="THOMAS_LH",
        to_account="TOTAL SYSTEM BALANCE",
        amount=10_000_000.00
    )

    print("[OMEGA TRANSFER COMPLETE]")
    print("TX_ID:", tx)
