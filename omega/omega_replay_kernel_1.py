#!/usr/bin/env python3
import psycopg2
import json
from decimal import Decimal
from collections import defaultdict

"""
OMEGA REPLAY KERNEL
Deterministic state reconstruction from ledger_events
(NO LIVE STATE DEPENDENCY)
"""

# ----------------------------
# REPLAY ENGINE
# ----------------------------
class ReplayKernel:

    def __init__(self, conn):
        self.conn = conn
        self.state = defaultdict(lambda: {
            "balance": Decimal("0"),
            "credits": Decimal("0"),
            "debits": Decimal("0"),
            "tx_count": 0
        })

    # ----------------------------
    # LOAD EVENTS (SOURCE OF TRUTH)
    # ----------------------------
    def load_events(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT wallet_id, direction, amount, created_at
                FROM ledger_entries
                ORDER BY created_at ASC
            """)
            return cur.fetchall()

    # ----------------------------
    # APPLY EVENT (PURE FUNCTION)
    # ----------------------------
    def apply(self, wallet_id, direction, amount):
        w = self.state[wallet_id]

        amt = Decimal(str(amount))

        if direction == "CREDIT":
            w["balance"] += amt
            w["credits"] += amt
        else:
            w["balance"] -= amt
            w["debits"] += amt

        w["tx_count"] += 1

    # ----------------------------
    # FULL REPLAY
    # ----------------------------
    def replay(self):
        events = self.load_events()

        for wallet_id, direction, amount, _ts in events:
            self.apply(wallet_id, direction, amount)

        return self.state


# ----------------------------
# EXECUTION ENTRY
# ----------------------------
def run():
    conn = psycopg2.connect(
        dbname="omega_bank",
        user="omega"
    )

    kernel = ReplayKernel(conn)
    state = kernel.replay()

    for wallet_id, data in state.items():
        print({
            "wallet_id": wallet_id,
            "reconstructed_balance": str(data["balance"]),
            "credits": str(data["credits"]),
            "debits": str(data["debits"]),
            "tx_count": data["tx_count"]
        })

if __name__ == "__main__":
    run()
