from omega_db_kernel_v1 import OmegaTransaction


def snapshot():
    with OmegaTransaction() as cur:
        cur.execute("""
            SELECT *
            FROM omega_events
            WHERE event_type IN (
                'SETTLEMENT_FINALIZED_V2',
                'SETTLEMENT_FINALIZED',
                'SEALED'
            )
            ORDER BY sequence_number ASC;
        """)
        events = cur.fetchall()

    print("🔁 OMEGA CLEAN REPLAY SNAPSHOT (STATE-AWARE)")

    seen = set()

    for e in events:
        key = (e["event_type"], e["aggregate_id"], e["amount"])

        if key in seen:
            continue

        seen.add(key)

        print(e["event_type"], e["aggregate_id"], e["amount"])

    return events


if __name__ == "__main__":
    snapshot()
