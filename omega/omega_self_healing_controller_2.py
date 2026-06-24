#!/usr/bin/env python3

"""
OMEGA SELF-HEALING CONTROLLER
-----------------------------
Observability-driven autonomous stabilization layer

DOES NOT MUTATE FINANCIAL STATE

Only:
- detects drift
- proposes corrections
- triggers safe system controls
"""

import psycopg2
import time
from collections import defaultdict


# =========================
# 1. SYSTEM HEALTH SCORING
# =========================

def compute_health(drift_report):
    total_drift = sum(abs(v["drift"]) for v in drift_report.values())

    if total_drift < 1:
        return 100
    elif total_drift < 1000:
        return 70
    elif total_drift < 100000:
        return 40
    else:
        return 10


# =========================
# 2. FAILURE DETECTOR
# =========================

def detect_failure_modes(drift_report):
    signals = {
        "HIGH_DRIFT": [],
        "NEGATIVE_BALANCE": [],
        "INCONSISTENT_LEDGER": []
    }

    for wallet, d in drift_report.items():

        if abs(d["drift"]) > 1000:
            signals["HIGH_DRIFT"].append(wallet)

        if d["live"] < 0:
            signals["NEGATIVE_BALANCE"].append(wallet)

        if abs(d["drift"]) > 0 and abs(d["drift"]) < 0.01:
            signals["INCONSISTENT_LEDGER"].append(wallet)

    return signals


# =========================
# 3. SELF-HEALING ACTION PLANNER
# =========================

def propose_actions(health_score, signals):
    actions = []

    if health_score < 50:
        actions.append({
            "action": "REDUCE_WORKER_THROUGHPUT",
            "reason": "system instability detected"
        })

    if signals["HIGH_DRIFT"]:
        actions.append({
            "action": "ENABLE_REPLAY_VERIFICATION",
            "targets": signals["HIGH_DRIFT"]
        })

    if signals["NEGATIVE_BALANCE"]:
        actions.append({
            "action": "QUARANTINE_WALLETS",
            "targets": signals["NEGATIVE_BALANCE"]
        })

    return actions


# =========================
# 4. SAFE CONTROL EXECUTOR (NO MONEY WRITES)
# =========================

def execute_controls(actions):
    for a in actions:
        print("[HEALING ACTION]", a)


# =========================
# 5. CONTROLLER LOOP
# =========================

def run():
    conn = psycopg2.connect(dbname="omega_bank", user="omega")
    cur = conn.cursor()

    print("[HEAL] Self-healing controller online...")

    while True:
        try:

            # load drift snapshot from consensus gate tables
            cur.execute("""
                SELECT wallet_id, live, replay, drift
                FROM obs_wallet_health
            """)

            drift_report = {}

            for w, live, replay, drift in cur.fetchall():
                drift_report[w] = {
                    "live": float(live),
                    "replay": float(replay),
                    "drift": float(drift)
                }

            health = compute_health(drift_report)
            signals = detect_failure_modes(drift_report)
            actions = propose_actions(health, signals)

            print("\n=== SELF-HEALING REPORT ===")
            print("HEALTH SCORE:", health)
            print("SIGNALS:", signals)
            print("ACTIONS:", actions)

            execute_controls(actions)

            time.sleep(3)

        except Exception as e:
            print("[HEAL ERROR]", e)
            time.sleep(2)


if __name__ == "__main__":
    run()
