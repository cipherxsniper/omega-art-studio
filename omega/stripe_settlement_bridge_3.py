import os
import sqlite3
import stripe
from dotenv import load_dotenv
import uuid

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
DB = "omega_ledger.db"

def credit_account(user_id, amount):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
        UPDATE accounts
        SET balance = balance + ?
        WHERE user_id=?
    """, (amount, user_id))

    tx_id = str(uuid.uuid4())

    cur.execute("""
        INSERT INTO ledger (id, tx_type, amount, status)
        VALUES (?, ?, ?, ?)
    """, (tx_id, "STRIPE_CREDIT", amount, "SETTLED"))

    conn.commit()
    conn.close()

def handle_payment_intent(event):
    amount = event["data"]["object"]["amount_received"] / 100

    # default routing (YOU can refine later)
    credit_account("OMEGA_REVENUE", amount)

    print("[STRIPE SETTLED]", amount)

def handle_event(event):
    if event["type"] == "payment_intent.succeeded":
        handle_payment_intent(event)

    return "OK"
