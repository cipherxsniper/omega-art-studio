#!/usr/bin/env python3
import psycopg2
from decimal import Decimal
from omega_replay_kernel import ReplayKernel

"""
OMEGA DUAL LEDGER CONSENSUS GATE
Truth validation layer between live state and replay state
"""

# ----------------------------
# FETCH LIVE WALLET STATE
# ----------------------------
def get_live_state(cur):
    cur.execute("""
        SELECT id, settled_balance
        FROM wallets
    """)
    return {
        row[0]: Decimal(str(row[1]))
        for row in cur.fetchall()
    }


# ----------------------------
# RUN REPLAY STATE
# ----------------------------
def get_replay_state(conn):
    kernel = ReplayKernel(conn)
    replay = kernel.replay()

    return {
        wallet_id: data["balance"]
        for wallet_id, data in replay.items()
    }


# ----------------------------
# CONSENSUS COMPARE ENGINE
# ----------------------------
def compare_states(live, replay, tolerance=Decimal("0.00")):
    drift_report = []

    all_wallets = set(live.keys()) | set(replay.keys())

    for wallet_id in all_wallets:
        live_val = live.get(wallet_id, Decimal("0"))
        replay_val = replay.get(wallet_id, Decimal("0"))

        delta = live_val - replay_val

        if abs(delta) > tolerance:
            drift_report.append({
                "wallet_id": wallet_id,
                "live": str(live_val),
                "replay": str(replay_val),
                "drift": str(delta),
                "status": "OUT_OF_CONSENSUS"
            })

    return drift_report


# ----------------------------
# MAIN GATE FUNCTION
# ----------------------------
def run_consensus_gate():
    conn = psycopg2.connect(dbname="omega_bank", user="omega")

    with conn.cursor() as cur:

        # 1. LIVE STATE
        live = get_live_state(cur)

    # 2. REPLAY STATE (SOURCE OF TRUTH)
    replay = get_replay_state(conn)

    # 3. COMPARE
    drift = compare_states(live, replay)

    # 4. OUTPUT DECISION
    if len(drift) == 0:
        print("\n[CONSENSUS GATE] PASS - SYSTEM VALID\n")
        return {"status": "PASS"}

    print("\n[CONSENSUS GATE] FAIL - DRIFT DETECTED\n")
    for d in drift:
        print(d)

    return {
        "status": "FAIL",
        "drift_count": len(drift),
        "drift": drift
    }


if __name__ == "__main__":
    run_consensus_gate()
