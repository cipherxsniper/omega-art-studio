#!/usr/bin/env python3

"""
OMEGA RECONCILIATION BOOTSTRAP
Deterministic ledger → reconciliation activation layer

Purpose:
- Attach reconciliation engine to existing Omega ledger state
- Ensure all accounts (including high-value treasury systems) are included
- Run idempotently (safe to re-execute)
"""

from omega_event_bus_core_v1 import connect_db
from omega_reconciliation_engine_v1 import reconcile_system


def run_reconciliation():
    conn = connect_db()

    try:
        print("=== OMEGA RECONCILIATION START ===")

        # This should pull ALL accounts already in your system
        # including TREASURY / CREDIT / RESERVE / INVESTMENT (~57B system state)
        result = reconcile_system(conn)

        print("[RECONCILIATION COMPLETE]")
        print(result)

    except Exception as e:
        print("[RECONCILIATION ERROR]", str(e))

    finally:
        conn.close()


if __name__ == "__main__":
    run_reconciliation()
