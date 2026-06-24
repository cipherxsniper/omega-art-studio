import psycopg2
import uuid
import json
from contextlib import contextmanager

DB_CONFIG = {
    "dbname": "omega_bank",
    "user": "omega",
    "host": "localhost",
    "port": 5432
}

@contextmanager
def tx():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def append_event(event_type, aggregate_id, payload, idempotency_key):
    with tx() as cur:
        cur.execute("""
            INSERT INTO ledger_events (
                id,
                event_type,
                aggregate_id,
                aggregate_type,
                payload,
                created_at,
                idempotency_key
            )
            VALUES (
                gen_random_uuid(),
                %s,
                %s,
                'WALLET',
                %s::jsonb,
                NOW(),
                %s
            )
            ON CONFLICT (idempotency_key) DO NOTHING
        """, (
            event_type,
            aggregate_id,
            json.dumps(payload),
            idempotency_key
        ))

        return True
