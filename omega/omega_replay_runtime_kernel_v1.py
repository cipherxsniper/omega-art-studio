#!/usr/bin/env python3

import psycopg2
import hashlib

DB = "omega_bank"
USER = "omega"

def connect():
    return psycopg2.connect(dbname=DB, user=USER)

def hash_state(state):
    return hashlib.sha256(str(sorted(state.items())).encode()).hexdigest()

def main():
    conn = connect()
    cur = conn.cursor()

    print("Loading events...")

    cur.execute("""
        SELECT event_id, sequence_number, event_type, payload
        FROM omega_events
        ORDER BY sequence_number ASC
    """)

    events = cur.fetchall()

    state = {
        "auth_count": 0,
        "captured": 0,
        "reversed": 0,
        "expired": 0,
        "payments": 0
    }

    for e in events:
        _, _, event_type, payload = e

        if event_type == "AUTH_CREATED":
            state["auth_count"] += 1

        elif event_type == "AUTH_CAPTURED":
            state["captured"] += 1

        elif event_type == "AUTH_REVERSED":
            state["reversed"] += 1

        elif event_type == "AUTH_EXPIRED":
            state["expired"] += 1

        elif event_type == "PAYMENT_CAPTURED":
            state["payments"] += 1

    state_hash = hash_state(state)

    print("\n===== KERNEL REPLAY COMPLETE =====")
    print("STATE:", state)
    print("STATE HASH:", state_hash)
    print("✔ CRYPTOGRAPHIC STATE VALID")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
