#!/usr/bin/env python3

import sqlite3
import json
import time
import uuid

DB = "omega_ledger.db"


def generate_event(account_id, event_type, amount):
    return {
        "event_id": str(uuid.uuid4()),
        "account_id": account_id,
        "type": event_type,
        "amount": amount,
        "timestamp": time.time()
    }


def run():
    print("💳 OMEGA TRANSACTION INGESTION CORE v1")

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # demo deterministic ingestion (safe seed events)
    seed_events = [
        generate_event("2109a4cc-a066-4698-a478-a786bf096318", "DEPOSIT", 1000),
        generate_event("c9e77383-1517-4913-bc8f-c600693f853b", "DEPOSIT", 500),
        generate_event("6a91636d-7ba3-435c-9ba3-01ccd2b37a14", "TRANSFER", -200),
        generate_event("8e06388c-0679-4e85-b5c5-ef96404fd8b4", "DEPOSIT", 10000)
    ]

    inserted = 0

    for e in seed_events:
        payload = json.dumps(e)

        cur.execute("""
            INSERT INTO ledger_events (id, type, payload, timestamp)
            VALUES (?, ?, ?, ?)
        """, (
            e["event_id"],
            e["type"],
            payload,
            str(e["timestamp"])
        ))

        inserted += 1

    conn.commit()

    print(json.dumps({
        "status": "INGESTION_COMPLETE",
        "events_inserted": inserted
    }, indent=2))

    conn.close()


if __name__ == "__main__":
    run()
