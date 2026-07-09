import sqlite3

conn = sqlite3.connect("billing.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stripe_customer_id TEXT UNIQUE,
    email TEXT,
    name TEXT,
    lead_id TEXT,
    created_at REAL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stripe_subscription_id TEXT UNIQUE,
    stripe_customer_id TEXT,
    status TEXT,
    price_id TEXT,
    current_period_start REAL,
    current_period_end REAL,
    cancel_at_period_end INTEGER DEFAULT 0,
    created_at REAL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stripe_invoice_id TEXT UNIQUE,
    stripe_customer_id TEXT,
    amount_paid REAL,
    status TEXT,
    created_at REAL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS payment_failures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stripe_customer_id TEXT,
    stripe_invoice_id TEXT,
    reason TEXT,
    created_at REAL
)
""")

conn.commit()
conn.close()

print("[OK] billing.db initialized")
