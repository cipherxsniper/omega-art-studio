import sqlite3
import time

DB = "billing.db"


class BillingStore:

    def save_customer(
        self,
        stripe_customer_id,
        email=None,
        name=None,
        lead_id=None
    ):
        conn = sqlite3.connect(DB)

        conn.execute("""
        INSERT OR IGNORE INTO customers (
            stripe_customer_id,
            email,
            name,
            lead_id,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """, (
            stripe_customer_id,
            email,
            name,
            lead_id,
            time.time()
        ))

        conn.commit()
        conn.close()

    def save_subscription(
        self,
        stripe_subscription_id,
        stripe_customer_id,
        status,
        price_id,
        current_period_start=None,
        current_period_end=None,
        cancel_at_period_end=0
    ):
        conn = sqlite3.connect(DB)

        conn.execute("""
        INSERT OR REPLACE INTO subscriptions (
            stripe_subscription_id,
            stripe_customer_id,
            status,
            price_id,
            current_period_start,
            current_period_end,
            cancel_at_period_end,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            stripe_subscription_id,
            stripe_customer_id,
            status,
            price_id,
            current_period_start,
            current_period_end,
            cancel_at_period_end,
            time.time()
        ))

        conn.commit()
        conn.close()

    def save_invoice(
        self,
        stripe_invoice_id,
        stripe_customer_id,
        amount_paid,
        status
    ):
        conn = sqlite3.connect(DB)

        conn.execute("""
        INSERT OR IGNORE INTO invoices (
            stripe_invoice_id,
            stripe_customer_id,
            amount_paid,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """, (
            stripe_invoice_id,
            stripe_customer_id,
            amount_paid,
            status,
            time.time()
        ))

        conn.commit()
        conn.close()

    def save_payment_failure(
        self,
        stripe_customer_id,
        stripe_invoice_id,
        reason
    ):
        conn = sqlite3.connect(DB)

        conn.execute("""
        INSERT INTO payment_failures (
            stripe_customer_id,
            stripe_invoice_id,
            reason,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """, (
            stripe_customer_id,
            stripe_invoice_id,
            reason,
            time.time()
        ))

        conn.commit()
        conn.close()


billing_store = BillingStore()
