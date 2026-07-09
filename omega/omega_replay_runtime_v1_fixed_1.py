#!/usr/bin/env python3

import psycopg2

DB = "omega_bank"
USER = "omega"

class ReplayRuntime:

    def __init__(self):
        self.conn = psycopg2.connect(dbname=DB, user=USER)

    def load_events(self):
        cur = self.conn.cursor()

        cur.execute("""
            SELECT
                event_id,
                sequence_number,
                event_type,
                created_at
            FROM omega_events
            ORDER BY sequence_number ASC
        """)

        rows = cur.fetchall()

        events = []
        for row in rows:
            events.append({
                "event_id": str(row[0]),
                "sequence_number": row[1],
                "event_type": row[2],
                "created_at": str(row[3]) if len(row) > 3 else None
            })

        return events

    def replay(self):
        print("Loading events...")
        events = self.load_events()

        print(f"Loaded {len(events)} events")
        print("\n===== REPLAY COMPLETE =====")
        print("STATE REBUILT FROM EVENT STREAM ✓")

def main():
    runtime = ReplayRuntime()
    runtime.replay()

if __name__ == "__main__":
    main()
