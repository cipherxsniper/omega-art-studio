import psycopg2, uuid, json, sys

DB = {"dbname":"omega_bank","user":"omega"}

def append_event(event_type, aggregate_id, aggregate_type, payload, idem_key=None):
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO ledger_events (
            event_type,
            aggregate_id,
            aggregate_type,
            payload,
            idempotency_key
        )
        VALUES (%s,%s,%s,%s,%s)
        RETURNING id;
    """, (
        event_type,
        aggregate_id,
        aggregate_type,
        json.dumps(payload),
        idem_key or str(uuid.uuid4())
    ))

    event_id = cur.fetchone()[0]
    conn.commit()
    conn.close()

    print("EVENT_APPENDED:", event_id)

if __name__ == "__main__":
    append_event(
        sys.argv[1],
        sys.argv[2],
        sys.argv[3],
        json.loads(sys.argv[4])
    )
