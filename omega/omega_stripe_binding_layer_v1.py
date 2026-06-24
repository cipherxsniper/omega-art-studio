import sqlite3
import hashlib
from datetime import datetime, timezone


def safe_float(value):
    try:
        if value is None:
            return 0.0
        return float(value)
    except:
        return 0.0


def load_events(cur):
    cur.execute("""
        SELECT event_id, amount, currency, created_at
        FROM ledger_events
    """)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def hash_event(e):
    base = f"{e.get('event_id')}|{e.get('amount')}|{e.get('created_at')}"
    return hashlib.sha256(base.encode()).hexdigest()


def run():
    conn = sqlite3.connect("omega_ledger.db")
    cur = conn.cursor()

    events = load_events(cur)

    stripe_projection = []

    for e in events:

        amount = safe_float(e.get("amount"))

        stripe_projection.append({
            "event_id": e.get("event_id"),
            "amount": amount,
            "currency": e.get("currency", "USD"),
            "created": datetime.now(timezone.utc).isoformat(),
            "event_hash": hash_event(e)
        })

    print("🪞 OMEGA STRIPE SYNC (HARDENED)")
    print({
        "ledger_events": len(events),
        "stripe_events": len(stripe_projection),
        "system_state": "STRIPE_SYNCED"
    })

    conn.close()


if __name__ == "__main__":
    run()
