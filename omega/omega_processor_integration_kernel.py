#!/usr/bin/env python3

"""
OMEGA PROCESSOR INTEGRATION KERNEL
-----------------------------------
Processor-agnostic payment orchestration layer

Responsibilities:
- PaymentIntent normalization
- Idempotent routing
- Processor adapter abstraction
- Event emission
- Reconciliation hooks
"""

import json
import time


# =========================
# 1. PROCESSOR ADAPTER LAYER
# =========================

class ProcessorAdapter:
    """
    Abstract interface for external payment processors
    (Stripe/Adyen/Bank rails/etc)
    """

    def authorize(self, payment_intent):
        raise NotImplementedError

    def capture(self, auth_id, amount):
        raise NotImplementedError

    def refund(self, transaction_id):
        raise NotImplementedError

    def reconcile(self, webhook_event):
        raise NotImplementedError


# =========================
# 2. PAYMENT INTENT NORMALIZER
# =========================

def normalize_intent(raw_event):
    """
    Converts any inbound event into a canonical PaymentIntent
    """
    if isinstance(raw_event, str):
        raw_event = json.loads(raw_event)

    return {
        "intent_id": raw_event.get("intent_id"),
        "type": raw_event.get("type"),
        "amount": float(raw_event.get("amount", 0)),
        "currency": raw_event.get("currency", "USD"),
        "merchant": raw_event.get("merchant"),
        "source": raw_event.get("source"),
        "idempotency_key": raw_event.get("idempotency_key")
    }


# =========================
# 3. IDEMPOTENCY GATE
# =========================

def check_idempotency(cur, key):
    cur.execute("""
        SELECT 1 FROM idempotency_keys WHERE key = %s
    """, (key,))
    return cur.fetchone() is not None


def mark_idempotent(cur, key):
    cur.execute("""
        INSERT INTO idempotency_keys(key, created_at)
        VALUES (%s, now())
        ON CONFLICT DO NOTHING
    """, (key,))


# =========================
# 4. EVENT ROUTER (CORE KERNEL)
# =========================

def route_payment(cur, processor, raw_event):
    intent = normalize_intent(raw_event)
    idem = intent["idempotency_key"]

    # 1. Idempotency guard
    if check_idempotency(cur, idem):
        return {"status": "DUPLICATE_IGNORED"}

    mark_idempotent(cur, idem)

    # 2. Route to processor (external system boundary)
    auth_result = processor.authorize(intent)

    # 3. Emit authorization event (internal ledger-safe event)
    cur.execute("""
        INSERT INTO settlement_queue (
            event_type,
            status,
            payload,
            idempotency_key,
            created_at
        )
        VALUES (%s,%s,%s,%s,now())
    """, (
        "AUTH_EVENT",
        "AUTHORIZED",
        json.dumps(auth_result),
        idem
    ))

    return auth_result


# =========================
# 5. WEBHOOK RECONCILIATION
# =========================

def reconcile_event(cur, event):
    """
    External processor callback handler
    """

    if isinstance(event, str):
        event = json.loads(event)

    event_type = event.get("type")

    if event_type == "CAPTURE":
        status = "CAPTURED"
    elif event_type == "AUTH":
        status = "AUTHORIZED"
    elif event_type == "REFUND":
        status = "REFUNDED"
    else:
        status = "UNKNOWN"

    cur.execute("""
        INSERT INTO reconciliation_snapshots (
            event_type,
            status,
            payload,
            created_at
        )
        VALUES (%s,%s,%s,now())
    """, (
        event_type,
        status,
        json.dumps(event)
    ))

    return {"reconciled": True, "status": status}


# =========================
# 6. MAIN LOOP (ORCHESTRATION ENGINE)
# =========================

def run_loop(conn, processor):
    cur = conn.cursor()

    while True:
        try:
            cur.execute("""
                SELECT payload
                FROM settlement_queue
                WHERE status = 'PENDING'
                LIMIT 1
            """)

            row = cur.fetchone()
            if not row:
                time.sleep(0.5)
                continue

            payload = row[0]
            route_payment(cur, processor, payload)

            conn.commit()

        except Exception as e:
            print("[KERNEL ERROR]", e)
            time.sleep(1)


# =========================
# 7. MOCK PROCESSOR (BOUNDARY ONLY)
# =========================

class MockProcessor(ProcessorAdapter):
    def authorize(self, payment_intent):
        return {
            "auth_id": "auth_" + str(payment_intent["idempotency_key"]),
            "status": "APPROVED",
            "amount": payment_intent["amount"]
        }


if __name__ == "__main__":
    import psycopg2

    conn = psycopg2.connect(dbname="omega_bank", user="omega")
    processor = MockProcessor()

    run_loop(conn, processor)
