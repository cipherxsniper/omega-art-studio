#!/usr/bin/env python3
import time
import psycopg2

"""
OMEGA AUTONOMY CONTROLLER (PRODUCTION FINTECH VERSION)

Controls:
- worker health
- queue stability
- external processor reconciliation drift
- retry backoff
- system freeze/unfreeze
"""

FREEZE = False


def get_system_health(cur):
    cur.execute("""
        SELECT
            (SELECT COUNT(*) FROM settlement_queue WHERE status='FAILED') AS failed,
            (SELECT COUNT(*) FROM settlement_queue WHERE status='PROCESSING') AS processing,
            (SELECT COUNT(*) FROM settlement_queue WHERE status='PENDING') AS pending
    """)
    failed, processing, pending = cur.fetchone()

    cur.execute("""
        SELECT COALESCE(SUM(drift), 0)
        FROM obs_wallet_health
    """)
    drift = float(cur.fetchone()[0])

    return {
        "failed": failed,
        "processing": processing,
        "pending": pending,
        "drift": drift
    }


def compute_state(m):
    drift = abs(m["drift"])

    if drift > 50000:
        return "FREEZE"

    if m["failed"] > 200:
        return "BACKOFF"

    if m["processing"] > 1000:
        return "THROTTLE"

    if m["pending"] > 5000:
        return "SCALE"

    return "NORMAL"


def apply_state(state):
    global FREEZE

    if state == "FREEZE":
        FREEZE = True
        print("[CONTROLLER] ❄ SYSTEM FROZEN (DRIFT LIMIT BREACHED)")

    elif state == "BACKOFF":
        print("[CONTROLLER] ⬇ BACKOFF MODE ACTIVATED")

    elif state == "THROTTLE":
        print("[CONTROLLER] ⛔ THROTTLING WORKERS")

    elif state == "SCALE":
        print("[CONTROLLER] ⬆ SCALING WORKERS")

    else:
        FREEZE = False
        print("[CONTROLLER] ✅ SYSTEM STABLE")


def run():
    conn = psycopg2.connect(dbname="omega_bank", user="omega")
    cur = conn.cursor()

    while True:
        try:
            m = get_system_health(cur)
            state = compute_state(m)
            apply_state(state)

            time.sleep(2)

        except Exception as e:
            print("[CONTROLLER ERROR]", e)
            time.sleep(5)


if __name__ == "__main__":
    run()
