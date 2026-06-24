#!/usr/bin/env python3

"""
Bridge external webhook events into reconciliation engine input stream.
READ ONLY — DOES NOT MODIFY LEDGER
"""

import sqlite3
import json

DB = "omega_ledger.db"


def fetch_external_webhook_events():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT id, type, payload, timestamp FROM events ORDER BY rowid ASC")
    rows = cur.fetchall()

    conn.close()

    return [
        {
            "id": r[0],
            "type": r[1],
            "payload": json.loads(r[2]) if r[2] else {},
            "timestamp": r[3]
        }
        for r in rows
    ]


def attach_external_feed(reconciliation_results):
    """
    Marks reconciliation output with external visibility context.
    """
    external = fetch_external_webhook_events()

    external_ids = set(e["id"] for e in external)

    for r in reconciliation_results:
        r["external_match"] = r["id"] in external_ids

    return reconciliation_results
