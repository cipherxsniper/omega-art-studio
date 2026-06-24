"""
OMEGA RECONCILIATION ENTRYPOINT
Links ALL accounts + Stripe + ledger + Thomas Lee Harvey account

NO REAL ARCHITECTURE CHANGE — ONLY WIRING FIX
"""

from omega_reconciliation_engine_v1 import reconcile_system
from omega_db_alignment_fix_v1 import connect_billing_db


def run_reconciliation():
    conn = connect_billing_db()

    print("=== OMEGA RECONCILIATION START ===")

    # THIS IS WHERE YOUR 57B SYSTEM SHOULD ATTACH
    # (ledger + subscriptions + identity graph)
    reconcile_system(conn)

    conn.commit()
    conn.close()

    print("=== RECONCILIATION COMPLETE ===")


if __name__ == "__main__":
    run_reconciliation()
