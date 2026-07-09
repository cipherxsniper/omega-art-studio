import psycopg2

DB = {
    "dbname": "omega_bank",
    "user": "omega",
    "password": "omega",
    "host": "localhost"
}

def rebuild():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT event_type, aggregate_id, payload
        FROM omega_events
        ORDER BY sequence_number ASC
    """)

    state = {}

    for event_type, wallet_id, payload in cur.fetchall():
        if wallet_id not in state:
            state[wallet_id] = {
                "settled": 0,
                "reserved": 0,
                "pending": 0
            }

        if event_type == "AUTH_APPROVED":
            amount = float(payload["amount"])
            state[wallet_id]["reserved"] += amount

    print(state)

if __name__ == "__main__":
    rebuild()
