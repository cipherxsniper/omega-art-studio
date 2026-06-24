import sqlite3
from decimal import Decimal, InvalidOperation


def safe_amount(value):
    try:
        if value is None:
            return Decimal("0.00")
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0.00")


def run():
    conn = sqlite3.connect("omega_ledger.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM ledger_events")
    rows = cur.fetchall()

    repaired = 0

    for row in rows:
        event_id = row[0]
        amount = row[2]

        clean_amount = safe_amount(amount)

        if amount != clean_amount:
            repaired += 1
            cur.execute(
                "UPDATE ledger_events SET amount = ? WHERE event_id = ?",
                (float(clean_amount), event_id)
            )

    conn.commit()
    conn.close()

    print("🧼 OMEGA LEDGER SANITIZER v1")
    print({
        "rows_repaired": repaired,
        "system_state": "LEDGER_SANITIZED"
    })


if __name__ == "__main__":
    run()
