import psycopg2
from psycopg2.extras import RealDictCursor
from omega_settlement_contracts_v1 import normalize_event, serialize_for_db

DB_CONFIG = {
    "dbname": "omega_bank",
    "user": "omega",
    "password": "",
    "host": "localhost"
}

class OmegaTransaction:
    def __enter__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cur = self.conn.cursor(cursor_factory=RealDictCursor)
        return self.cur

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.cur.close()
        self.conn.close()


def insert_event(cur, event):

    # stage 1 already done upstream, but safe recheck
    event = normalize_event(event)

    # stage 2: DB-safe serialization
    safe_event = serialize_for_db(event)

    cur.execute(
        """
        INSERT INTO omega_events (
            event_id,
            event_type,
            aggregate_id,
            aggregate_type,
            merchant_id,
            wallet_id,
            amount,
            currency,
            timestamp,
            version,
            idempotency_key,
            payload
        )
        VALUES (
            %(event_id)s,
            %(event_type)s,
            %(aggregate_id)s,
            %(aggregate_type)s,
            %(merchant_id)s,
            %(wallet_id)s,
            %(amount)s,
            %(currency)s,
            %(timestamp)s,
            %(version)s,
            %(idempotency_key)s,
            %(payload)s
        )
        """,
        safe_event
    )
