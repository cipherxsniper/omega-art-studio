import time
import sqlite3
import json
import uuid

from core.omega_ledger import ledger

QUEUE_DB = "event_queue.db"
LEDGER_DB = "omega_ledger.db"

SYSTEM = "SYSTEM"
REVENUE = "REVENUE"


def fetch():
    conn = sqlite3.connect(QUEUE_DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, type, payload
        FROM queue
        WHERE status='pending'
    """)

    rows = cur.fetchall()
    conn.close()

    return rows


def mark(job_id):
    conn = sqlite3.connect(QUEUE_DB)

    conn.execute("""
        UPDATE queue
        SET status='done'
        WHERE id=?
    """, (job_id,))

    conn.commit()
    conn.close()


def handle_payment(event_type, event):
    data = event["data"]["object"]

    tx_id = event["id"]

    amount = None

    if "amount_total" in data:
        amount = data["amount_total"] / 100

    elif "amount_received" in data:
        amount = data["amount_received"] / 100

    elif "amount_paid" in data:
        amount = data["amount_paid"] / 100

    if amount is None:
        print("[WORKER] no amount")
        return

    print(f"[LEDGER] Posting {amount}")

    ledger.post_transaction(
        tx_id=tx_id,
        debit_acc=SYSTEM,
        credit_acc=REVENUE,
        amount=amount,
        source="stripe"
    )


def handle_subscription_created(event):
    data = event["data"]["object"]

    subscription_id = data["id"]
    customer_id = data["customer"]

    status = data["status"]

    start = data["current_period_start"]
    end = data["current_period_end"]

    cancel = int(data["cancel_at_period_end"])

    price_id = (
        data["items"]["data"][0]["price"]["id"]
    )

    conn = sqlite3.connect(LEDGER_DB)

    conn.execute("""
        INSERT OR REPLACE INTO subscriptions
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        subscription_id,
        customer_id,
        status,
        price_id,
        start,
        end,
        cancel,
        time.time()
    ))

    conn.commit()
    conn.close()

    print(f"[SUBSCRIPTION] ACTIVE {subscription_id}")


def handle_payment_failed(event):
    data = event["data"]["object"]

    customer_id = data["customer"]

    subscription_id = data["subscription"]

    amount_due = data["amount_due"] / 100

    attempt_count = data["attempt_count"]

    conn = sqlite3.connect(LEDGER_DB)

    conn.execute("""
        INSERT INTO payment_failures
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        str(uuid.uuid4()),
        customer_id,
        subscription_id,
        amount_due,
        attempt_count,
        time.time()
    ))

    conn.execute("""
        UPDATE subscriptions
        SET status='past_due'
        WHERE subscription_id=?
    """, (subscription_id,))

    conn.commit()
    conn.close()

    print(f"[PAYMENT FAILED] {subscription_id}")


def handle(event_type, event):

    if event_type in [
        "payment_intent.succeeded",
        "invoice.paid",
        "checkout.session.completed"
    ]:
        handle_payment(event_type, event)

    elif event_type == "customer.subscription.created":
        handle_subscription_created(event)

    elif event_type == "invoice.payment_failed":
        handle_payment_failed(event)

    else:
        print(f"[IGNORED] {event_type}")


while True:

    jobs = fetch()

    for job in jobs:

        job_id, event_type, payload = job

        event = json.loads(payload)

        print(f"[WORKER] {event_type}")

        handle(event_type, event)

        mark(job_id)

    time.sleep(2)
