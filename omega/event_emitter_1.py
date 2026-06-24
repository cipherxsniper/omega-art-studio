#!/usr/bin/env python3

import uuid
import json
import psycopg2

DB_NAME = "omega_bank"
DB_USER = "omega"

def get_db():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER
    )

def emit_event(
    event_type,
    aggregate_id,
    aggregate_type,
    payload,
    idempotency_key
):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS connector_event_log (
            id UUID PRIMARY KEY,
            idempotency_key TEXT UNIQUE NOT NULL,
            event_type TEXT NOT NULL,
            aggregate_id UUID,
            aggregate_type TEXT,
            payload JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    cur.execute("""
        SELECT id
        FROM connector_event_log
        WHERE idempotency_key = %s
    """, (idempotency_key,))

    existing = cur.fetchone()

    if existing:
        conn.commit()
        cur.close()
        conn.close()

        return {
            "status": "DUPLICATE_EVENT",
            "event_id": str(existing[0])
        }

    event_id = str(uuid.uuid4())

    cur.execute("""
        INSERT INTO connector_event_log (
            id,
            idempotency_key,
            event_type,
            aggregate_id,
            aggregate_type,
            payload
        )
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (
        event_id,
        idempotency_key,
        event_type,
        aggregate_id,
        aggregate_type,
        json.dumps(payload)
    ))

    cur.execute("""
        INSERT INTO ledger_events (
            id,
            event_type,
            aggregate_id,
            aggregate_type,
            payload,
            created_at
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            NOW()
        )
    """, (
        event_id,
        event_type,
        aggregate_id,
        aggregate_type,
        json.dumps(payload)
    ))

    conn.commit()

    cur.close()
    conn.close()

    return {
        "status": "EVENT_EMITTED",
        "event_id": event_id,
        "event_type": event_type
    }

