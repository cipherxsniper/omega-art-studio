#!/usr/bin/env python3

import psycopg2
import time
import json
from datetime import datetime
from omega_replay_engine import replay

DB = "omega_bank"
USER = "omega"

DRIFT_THRESHOLD = 0.01

def conn():
    return psycopg2.connect(
        dbname=DB,
        user=USER
    )

# -----------------------------------
# FETCH LIVE CREDIT STATE
# -----------------------------------
def fetch_live_state(cur):
    cur.execute("""
        SELECT wallet_id, current_limit
        FROM credit_policy_state
    """)

    rows = cur.fetchall()

    state = {}

    for r in rows:
        state[str(r[0])] = float(r[1])

    return state

# -----------------------------------
# FETCH EVENT STREAM
# -----------------------------------
def fetch_event_stream(cur):
    cur.execute("""
        SELECT
            wallet_id,
            amount,
            merchant_risk,
            velocity_1m
        FROM transaction_stream
        ORDER BY created_at ASC
    """)

    rows = cur.fetchall()

    events = []

    for r in rows:
        events.append({
            "wallet_id": str(r[0]),
            "amount": float(r[1]),
            "merchant_risk": float(r[2]),
            "velocity_1m": float(r[3])
        })

    return events

# -----------------------------------
# DRIFT CHECK
# -----------------------------------
def compare_states(live, replayed):
    drift = []

    wallets = set(list(live.keys()) + list(replayed.keys()))

    for w in wallets:
        live_limit = float(live.get(w, 0))
        replay_limit = float(replayed.get(w, 0))

        delta = abs(live_limit - replay_limit)

        if delta > DRIFT_THRESHOLD:
            drift.append({
                "wallet_id": w,
                "live": live_limit,
                "replay": replay_limit,
                "delta": delta
            })

    return drift

# -----------------------------------
# QUARANTINE
# -----------------------------------
def quarantine_wallet(cur, wallet_id):
    cur.execute("""
        UPDATE credit_policy_state
        SET state = 'QUARANTINED',
            last_updated = NOW()
        WHERE wallet_id = %s
    """, (wallet_id,))

# -----------------------------------
# AUDIT LOG
# -----------------------------------
def log_drift(cur, item):
    cur.execute("""
        INSERT INTO consensus_drift_log (
            wallet_id,
            live_limit,
            replay_limit,
            delta,
            detected_at
        )
        VALUES (%s, %s, %s, %s, NOW())
    """, (
        item["wallet_id"],
        item["live"],
        item["replay"],
        item["delta"]
    ))

# -----------------------------------
# MAIN LOOP
# -----------------------------------
def run():
    print("OMEGA CONSENSUS GATE ONLINE")

    c = conn()

    while True:
        try:
            cur = c.cursor()

            live_state = fetch_live_state(cur)

            events = fetch_event_stream(cur)

            replay_state = replay(events)

            drift = compare_states(
                live_state,
                replay_state
            )

            if drift:
                print("\n[CONSENSUS DRIFT DETECTED]")
                print(json.dumps(drift, indent=2))

                for item in drift:
                    quarantine_wallet(
                        cur,
                        item["wallet_id"]
                    )

                    log_drift(cur, item)

            else:
                print(
                    "[" +
                    datetime.utcnow().isoformat() +
                    "] CONSENSUS OK"
                )

            c.commit()

            time.sleep(2)

        except Exception as e:
            c.rollback()
            print("[CONSENSUS ERROR]", e)
            time.sleep(3)

if __name__ == "__main__":
    run()
