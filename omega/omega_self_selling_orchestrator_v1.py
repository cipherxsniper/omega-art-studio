#!/usr/bin/env python3

import os
import time
import json
import sqlite3
import traceback
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# OMEGA CORE CONFIG
# ─────────────────────────────────────────────

CEO_NAME = "Thomas Lee Harvey"
COMPANY = "Omega AI"
SUPPORT_EMAIL = "omegaops.ai@gmail.com"

STRIPE_PAYMENT_LINK = os.getenv(
    "OMEGA_STRIPE_PAYMENT_LINK",
    "https://buy.stripe.com/"
)

DB_PATH = "omega_self_selling.db"

# ─────────────────────────────────────────────
# IMPORT ENGINES
# ─────────────────────────────────────────────

from omega_real_lead_scraper_v1 import scrape_local_service_leads
from omega_live_outbound_engine_v1 import send_outreach_email
from omega_reply_intelligence_v1 import classify_reply
from omega_crm_state_machine_v1 import update_crm_state

# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB_PATH)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        business_name TEXT,
        niche TEXT,
        status TEXT,
        created_at REAL
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS outreach (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        status TEXT,
        sent_at REAL
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        activated_at REAL
    )
    """)

    conn.commit()
    return conn

# ─────────────────────────────────────────────
# SAFE DB EXECUTION
# ─────────────────────────────────────────────

def safe_execute(conn, query, values=()):
    retries = 3

    while retries > 0:
        try:
            conn.execute(query, values)
            conn.commit()
            return True

        except sqlite3.OperationalError:
            retries -= 1
            time.sleep(0.25)

    return False

# ─────────────────────────────────────────────
# STRIPE CHECKOUT
# ─────────────────────────────────────────────

def create_checkout(lead):

    return {
        "status": "checkout_created",
        "checkout_url": STRIPE_PAYMENT_LINK,
        "email": lead["email"]
    }

# ─────────────────────────────────────────────
# CUSTOMER ACTIVATION
# ─────────────────────────────────────────────

def activate_customer(conn, lead):

    safe_execute(
        conn,
        """
        INSERT OR IGNORE INTO customers
        (email, activated_at)
        VALUES (?, ?)
        """,
        (
            lead["email"],
            time.time()
        )
    )

    return {
        "status": "customer_activated",
        "email": lead["email"]
    }

# ─────────────────────────────────────────────
# PROCESS LEAD
# ─────────────────────────────────────────────

def process_lead(conn, lead):

    result = {
        "lead": lead
    }

    # Save lead
    safe_execute(
        conn,
        """
        INSERT OR IGNORE INTO leads
        (email, business_name, niche, status, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            lead["email"],
            lead.get("business_name", ""),
            lead.get("niche", ""),
            "captured",
            time.time()
        )
    )

    # Send outreach
    outreach = send_outreach_email(
        to_email=lead["email"],
        business_name=lead.get("business_name", "Business"),
        niche=lead.get("niche", "local business"),
        sender=SUPPORT_EMAIL
    )

    result["outreach"] = outreach

    safe_execute(
        conn,
        """
        INSERT INTO outreach
        (email, status, sent_at)
        VALUES (?, ?, ?)
        """,
        (
            lead["email"],
            outreach.get("status", "sent"),
            time.time()
        )
    )

    # Simulated reply intelligence
    reply = classify_reply(
        "Yes, interested in getting more leads."
    )

    result["reply"] = reply

    # CRM Update
    crm = update_crm_state(
        lead["email"],
        reply.get("intent", "interested")
    )

    result["crm"] = crm

    # Stripe checkout
    checkout = create_checkout(lead)

    result["checkout"] = checkout

    # Activate customer
    onboarding = activate_customer(conn, lead)

    result["onboarding"] = onboarding

    result["status"] = "CLOSED_LOOP"

    return result

# ─────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────

def main():

    conn = init_db()

    print("\n=== OMEGA SELF-SELLING ORCHESTRATOR ===")

    while True:

        try:

            leads = scrape_local_service_leads()

            if not leads:
                print("[OMEGA] No leads found.")
                time.sleep(15)
                continue

            for lead in leads:

                try:

                    print(f"\n[OMEGA] Processing -> {lead['email']}")

                    result = process_lead(conn, lead)

                    print(json.dumps(result, indent=2))

                    time.sleep(3)

                except Exception as e:
                    print("[LEAD FAILURE]")
                    traceback.print_exc()

            print("\n[OMEGA] Cycle complete.")
            time.sleep(20)

        except KeyboardInterrupt:
            print("\n[OMEGA] Shutdown requested.")
            break

        except Exception:
            traceback.print_exc()
            time.sleep(10)

if __name__ == "__main__":
    main()
