import psycopg2
from decimal import Decimal

def replay(conn, wallet_id):

    cur = conn.cursor()

    cur.execute("""
        SELECT event_type, payload
        FROM ledger_events
        WHERE aggregate_id = %s
        ORDER BY sequence_number ASC
    """, (wallet_id,))

    settled = Decimal("0")
    reserved = Decimal("0")
    pending = Decimal("0")

    for event_type, payload in cur.fetchall():

        amount = Decimal(payload.get("amount", "0"))

        if event_type == "DEPOSIT":
            settled += amount

        elif event_type == "AUTH_HOLD":
            reserved += amount

        elif event_type == "SETTLE":
            reserved -= amount
            settled -= amount

    return {
        "settled_balance": settled,
        "reserved_balance": reserved,
        "available": settled - reserved
    }
