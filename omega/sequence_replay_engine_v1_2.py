#!/usr/bin/env python3

import psycopg2
from collections import defaultdict

DB_NAME = "omega_bank"
DB_USER = "omega"
DB_PASSWORD = ""
DB_HOST = "localhost"
DB_PORT = "5432"


def db():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )


class SequenceViolation(Exception):
    pass


def load_events(cur):

    cur.execute("""
        SELECT
            event_id,
            event_type,
            aggregate_id,
            aggregate_type,
            payload,
            sequence_number
        FROM omega_events
        ORDER BY aggregate_id ASC, sequence_number ASC
    """)

    return cur.fetchall()


def validate_sequence(events):

    by_aggregate = defaultdict(list)

    for e in events:
        by_aggregate[e[2]].append(e)

    for agg_id, evts in by_aggregate.items():

        expected = 1

        for evt in evts:

            seq = evt[5]

            if seq != expected:
                raise SequenceViolation(
                    f"Sequence gap detected in {agg_id}: expected {expected}, got {seq}"
                )

            expected += 1


def replay(events):

    state = {}

    for e in events:

        event_type = e[1]
        payload = e[4]

        if event_type == "AUTH_CREATED":
            state[e[2]] = {
                "auth": payload,
                "status": "CREATED"
            }

        elif event_type == "AUTH_CAPTURED":
            state[e[2]]["status"] = "CAPTURED"

        elif event_type == "PAYMENT_CAPTURED":
            state[e[2]]["status"] = "SETTLED"

        elif event_type == "AUTH_REVERSED":
            state[e[2]]["status"] = "REVERSED"

        elif event_type == "AUTH_EXPIRED":
            state[e[2]]["status"] = "EXPIRED"

    return state


def main():

    conn = db()

    try:

        with conn.cursor() as cur:

            events = load_events(cur)

            print(f"Loaded {len(events)} events")

            validate_sequence(events)

            state = replay(events)

            print("\n===== REPLAY COMPLETE =====")
            print("SEQUENCE VALIDATED ✓")
            print(f"AUTH COUNT: {len(state)}")

    finally:

        conn.close()


if __name__ == "__main__":
    main()
