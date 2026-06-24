#!/usr/bin/env python3

"""
OMEGA BANK CONTROL PLANE UI (TERMUX)
------------------------------------
Neon-green financial observability console

READ-ONLY CONTROL SURFACE
SAFE OPERATIONS ONLY
"""

import os
import time
import psycopg2

GREEN = "\033[92m"
RESET = "\033[0m"
BOLD = "\033[1m"


# =========================
# UI RENDER HELPERS
# =========================

def clear():
    os.system("clear")


def header():
    print(GREEN + BOLD)
    print("===========================================")
    print("        OMEGA BANK CONTROL PLANE")
    print("        FINANCIAL OPERATIONS UI")
    print("===========================================")
    print(RESET)


# =========================
# DATA FETCHERS
# =========================

def fetch_wallets(cur):
    cur.execute("""
        SELECT id, settled_balance
        FROM wallets
        ORDER BY settled_balance DESC
        LIMIT 10
    """)
    return cur.fetchall()


def fetch_drift(cur):
    cur.execute("""
        SELECT wallet_id, drift
        FROM obs_wallet_health
        ORDER BY ABS(drift) DESC
        LIMIT 10
    """)
    return cur.fetchall()


def fetch_queue(cur):
    cur.execute("""
        SELECT status, COUNT(*)
        FROM settlement_queue
        GROUP BY status
    """)
    return cur.fetchall()


def fetch_risk(cur):
    cur.execute("""
        SELECT event_type, status, created_at
        FROM invariant_failures
        ORDER BY created_at DESC
        LIMIT 5
    """)
    return cur.fetchall()


# =========================
# RENDER PANELS
# =========================

def render_wallets(wallets):
    print(GREEN + "[WALLETS TOP 10]" + RESET)
    for w, b in wallets:
        print(f"  {w} -> {b}")
    print()


def render_drift(drift):
    print(GREEN + "[DRIFT ALERTS]" + RESET)
    for w, d in drift:
        print(f"  {w} -> drift: {d}")
    print()


def render_queue(queue):
    print(GREEN + "[QUEUE STATE]" + RESET)
    for status, count in queue:
        print(f"  {status}: {count}")
    print()


def render_risk(risk):
    print(GREEN + "[RISK SIGNALS]" + RESET)
    for e, s, t in risk:
        print(f"  {e} | {s} | {t}")
    print()


# =========================
# CONTROL LOOP
# =========================

def run():
    conn = psycopg2.connect(dbname="omega_bank", user="omega")
    cur = conn.cursor()

    while True:
        clear()
        header()

        try:
            wallets = fetch_wallets(cur)
            drift = fetch_drift(cur)
            queue = fetch_queue(cur)
            risk = fetch_risk(cur)

            render_wallets(wallets)
            render_drift(drift)
            render_queue(queue)
            render_risk(risk)

            print(GREEN + BOLD + "[SYSTEM STATUS] LIVE" + RESET)
            print("refreshing in 2s...")

        except Exception as e:
            print("[UI ERROR]", e)

        time.sleep(2)


if __name__ == "__main__":
    run()
