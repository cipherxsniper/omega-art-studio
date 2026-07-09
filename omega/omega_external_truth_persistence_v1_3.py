#!/usr/bin/env python3

import sqlite3
import json
import hashlib
from datetime import datetime, UTC

DB = "omega_ledger.db"
SOURCE_FILE = "stripe_replay.json"


def connect():
    return sqlite3.connect(DB)


def ensure_tables(cur):

    cur.execute("""
        CREATE TABLE IF NOT EXISTS external_truth_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_event_id TEXT UNIQUE,
            provider TEXT,
            event_type TEXT,
            payload TEXT,
            payload_hash TEXT,
            received_at TEXT,
            persisted_at TEXT,
            deterministic_hash TEXT
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_external_event_id
        ON external_truth_snapshots(external_event_id)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_external_provider
        ON external_truth_snapshots(provider)
    """)


def load_external_events():
    try:
        with open(SOURCE_FILE, "r") as f:
            data = json.load(f)

            if isinstance(data, dict):
                return [data]

            if isinstance(data, list):
                return data

            return []

    except Exception:
        return []


def stable_json(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def sha256(data):
    return hashlib.sha256(data.encode()).hexdigest()


def snapshot_exists(cur, external_event_id):

    cur.execute("""
        SELECT 1
        FROM external_truth_snapshots
        WHERE external_event_id = ?
        LIMIT 1
    """, (external_event_id,))

    return cur.fetchone() is not None


def normalize_event(event):

    external_event_id = (
        event.get("id")
        or event.get("event_id")
        or event.get("stripe_event_id")
    )

    provider = (
        event.get("provider")
        or "stripe"
    )

    event_type = (
        event.get("type")
        or event.get("event_type")
        or "UNKNOWN"
    )

    received_at = (
        event.get("timestamp")
        or datetime.now(UTC).isoformat()
    )

    return {
        "external_event_id": external_event_id,
        "provider": provider,
        "event_type": event_type,
        "payload": event,
        "received_at": received_at
    }


def persist_snapshot(cur, normalized):

    payload_json = stable_json(normalized["payload"])

    payload_hash = sha256(payload_json)

    deterministic_input = stable_json({
        "external_event_id": normalized["external_event_id"],
        "provider": normalized["provider"],
        "event_type": normalized["event_type"],
        "payload_hash": payload_hash,
        "received_at": normalized["received_at"]
    })

    deterministic_hash = sha256(deterministic_input)

    cur.execute("""
        INSERT INTO external_truth_snapshots (
            external_event_id,
            provider,
            event_type,
            payload,
            payload_hash,
            received_at,
            persisted_at,
            deterministic_hash
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        normalized["external_event_id"],
        normalized["provider"],
        normalized["event_type"],
        payload_json,
        payload_hash,
        normalized["received_at"],
        datetime.now(UTC).isoformat(),
        deterministic_hash
    ))

    return {
        "external_event_id": normalized["external_event_id"],
        "payload_hash": payload_hash,
        "deterministic_hash": deterministic_hash
    }


def run():

    conn = connect()
    cur = conn.cursor()

    ensure_tables(cur)

    external_events = load_external_events()

    persisted = []

    for event in external_events:

        normalized = normalize_event(event)

        event_id = normalized["external_event_id"]

        if not event_id:
            continue

        if snapshot_exists(cur, event_id):
            continue

        result = persist_snapshot(cur, normalized)

        persisted.append(result)

    conn.commit()
    conn.close()

    print("🧾 EXTERNAL TRUTH PERSISTENCE v1")

    if not persisted:
        print("NO_NEW_EXTERNAL_SNAPSHOTS")
        return

    for item in persisted:
        print(json.dumps(item, indent=2))


if __name__ == "__main__":
    run()

