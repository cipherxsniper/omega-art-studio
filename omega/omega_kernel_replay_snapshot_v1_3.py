from omega_db_kernel_v1 import OmegaTransaction

def snapshot():
    with OmegaTransaction() as cur:
        cur.execute("SELECT * FROM omega_events ORDER BY sequence_number ASC;")
        events = cur.fetchall()

    print("🔁 OMEGA REPLAY SNAPSHOT")
    for e in events:
        print(e["event_type"], e["aggregate_id"], e["amount"])

    return events


if __name__ == "__main__":
    snapshot()
