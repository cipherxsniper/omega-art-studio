# ================================
# OMEGA EVENT LEDGER ENGINE
# ================================

import sqlite3

DB_PATH = "omega_ledger.db"


def get_ledger_snapshot():
    """
    Returns full ledger state for control plane / API / Telegram UI
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT account_id, balance
        FROM accounts
    """)
    rows = cur.fetchall()

    cur.execute("""
        SELECT COUNT(*) FROM ledger_events
    """)
    event_count = cur.fetchone()[0]

    total = sum(r[1] for r in rows)

    return {
        "accounts": [
            {"account_id": r[0], "balance": float(r[1])}
            for r in rows
        ],
        "total_balance": float(total),
        "event_count": int(event_count)
    }


# (optional compatibility alias if other modules expect it)
def run():
    return get_ledger_snapshot()
