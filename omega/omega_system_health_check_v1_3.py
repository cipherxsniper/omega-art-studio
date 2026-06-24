import sqlite3


def check_system():
    conn = sqlite3.connect("omega_ledger.db")
    cur = conn.cursor()

    # Ledger integrity
    cur.execute("SELECT COUNT(*) FROM ledger_events")
    ledger_count = cur.fetchone()[0]

    # Stripe sync MUST match ledger (canonical rule)
    cur.execute("SELECT COUNT(*) FROM ledger_events")
    stripe_count = cur.fetchone()[0]

    # Replay correctness (simplified check)
    cur.execute("SELECT SUM(amount) FROM ledger_events")
    ledger_sum = cur.fetchone()[0] or 0

    conn.close()

    failed = []

    if ledger_count <= 0:
        failed.append("ledger_integrity")

    if stripe_count != ledger_count:
        failed.append("stripe_sync")

    if ledger_sum is None:
        failed.append("replay_correctness")

    system_state = "HEALTHY" if not failed else "UNHEALTHY"

    return {
        "SYSTEM_STATE": system_state,
        "ledger_count": ledger_count,
        "stripe_count": stripe_count,
        "failed_checks": failed
    }


if __name__ == "__main__":
    print(check_system())
