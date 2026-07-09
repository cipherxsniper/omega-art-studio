import json
import psycopg2

DB_NAME = "omega_bank"
DB_USER = "omega"


def append_event(event):

    conn = psycopg2.connect(
        database=DB_NAME,
        user=DB_USER
    )

    cur = conn.cursor()

    cur.execute("""
        INSERT INTO omega_events (
            event_id,
            aggregate_id,
            event_type,
            payload
        )
        VALUES (%s, %s, %s, %s)
    """, (
        event["event_id"],
        event["aggregate_id"],
        event["event_type"],
        json.dumps(event["payload"])
    ))

    conn.commit()
    conn.close()

    return {
        "status": "EVENT_APPENDED",
        "event_id": event["event_id"]
    }


if __name__ == "__main__":

    test_event = {
        "event_id": "00000000-0000-0000-0000-000000000001",
        "aggregate_id": "00000000-0000-0000-0000-000000000000",
        "event_type": "TEST_EVENT",
        "payload": {
            "hello": "world"
        }
    }

    print(append_event(test_event))
