#!/usr/bin/env python3

"""
OMEGA REPLAY DETERMINISM ENGINE
--------------------------------
Event-sourced full system reconstruction layer

Guarantees:
- deterministic rebuild from ledger only
- no dependency on runtime state
- audit-grade reproducibility
"""

import psycopg2
from collections import defaultdict


# =========================
# 1. LOAD EVENT STREAM
# =========================

def load_events(cur):
    cur.execute("""
        SELECT transaction_id, wallet_id, direction, amount, created_at
        FROM ledger_entries
        ORDER BY created_at ASC
    """)
    return cur.fetchall()


# =========================
# 2. DETERMINISTIC REDUCER
# =========================

def replay(events):
    wallets = defaultdict(float)

    for tx_id, wallet_id, direction, amount, ts in events:

        if direction == "CREDIT":
            wallets[wallet_id] += float(amount)

        elif direction == "DEBIT":
            wallets[wallet_id] -= float(amount)

        else:
            # unknown event types are ignored deterministically
            continue

    return wallets


# =========================
# 3. LIVE STATE LOAD
# =========================

def load_live_state(cur):
    cur.execute("""
        SELECT id, settled_balance
        FROM wallets
    """)
    return {w: float(b) for w, b in cur.fetchall()}


# =========================
# 4. DRIFT ANALYSIS
# =========================

def compute_drift(live, replayed):
    drift_report = {}

    all_wallets = set(live.keys()) | set(replayed.keys())

    for w in all_wallets:
        live_val = live.get(w, 0.0)
        replay_val = replayed.get(w, 0.0)

        drift_report[w] = {
            "live": live_val,
            "replay": replay_val,
            "drift": live_val - replay_val
        }

    return drift_report


# =========================
# 5. CONSISTENCY SCORE
# =========================

def system_score(drift_report):
    total_drift = sum(abs(v["drift"]) for v in drift_report.values())
    return total_drift


# =========================
# 6. MAIN REPLAY ENGINE
# =========================

def run():
    conn = psycopg2.connect(dbname="omega_bank", user="omega")
    cur = conn.cursor()

    print("[REPLAY] Loading ledger events...")
    events = load_events(cur)

    print("[REPLAY] Reconstructing state...")
    replayed_state = replay(events)

    print("[REPLAY] Loading live state...")
    live_state = load_live_state(cur)

    print("[REPLAY] Computing drift...")
    drift = compute_drift(live_state, replayed_state)

    score = system_score(drift)

    print("\n=== SYSTEM DRIFT REPORT ===")
    for wallet, data in drift.items():
        print(wallet, data)

    print("\nTOTAL SYSTEM DRIFT:", score)

    if score == 0:
        print("[OK] SYSTEM IS FULLY DETERMINISTIC")
    else:
        print("[WARN] STATE DIVERGENCE DETECTED")


if __name__ == "__main__":
    run()
