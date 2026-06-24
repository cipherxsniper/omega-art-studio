#!/usr/bin/env python3

import psycopg2
import time
import os
import sys
from datetime import datetime

DB = "omega_bank"
USER = "omega"

GREEN = "\033[92m"
CYAN = "\033[96m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"

def clear():
    os.system("clear")

def header():
    print(GREEN + BOLD + """
===========================================
        OMEGA FULL CONTROL PLANE
        FINANCIAL OPERATIONS TERMINAL
===========================================
""" + RESET)

def connect():
    return psycopg2.connect(dbname=DB, user=USER)

def safe_query(conn, q):
    try:
        with conn.cursor() as cur:
            cur.execute(q)
            if cur.description:
                return cur.fetchall()
            return []
    except Exception as e:
        conn.rollback()
        return [("ERROR", str(e))]

def format_table(rows):
    if not rows:
        return "EMPTY"
    return "\n".join([str(r) for r in rows])

def run():
    conn = connect()

    while True:
        try:
            clear()
            header()

            # -------------------------
            # WALLET HEALTH DASHBOARD
            # -------------------------
            wallets = safe_query(conn, """
                SELECT id, settled_balance, ledger_balance, drift
                FROM obs_wallet_health
                ORDER BY ABS(drift) DESC
                LIMIT 10;
            """)

            print(CYAN + "\n[ LIVE WALLETS ]" + RESET)
            print(format_table(wallets))

            # -------------------------
            # QUEUE HEALTH
            # -------------------------
            queue = safe_query(conn, """
                SELECT status, COUNT(*)
                FROM settlement_queue
                GROUP BY status
                ORDER BY status;
            """)

            print(YELLOW + "\n[ QUEUE STATE ]" + RESET)
            print(format_table(queue))

            # -------------------------
            # DRIFT ALERTS
            # -------------------------
            drift = safe_query(conn, """
                SELECT wallet_id, drift, settled_balance, ledger_balance
                FROM obs_drift_alerts
                ORDER BY ABS(drift) DESC
                LIMIT 10;
            """)

            print(RED + "\n[ DRIFT ALERTS ]" + RESET)
            print(format_table(drift))

            # -------------------------
            # RISK EVENTS
            # -------------------------
            risk = safe_query(conn, """
                SELECT type, status, created_at
                FROM invariant_failures
                ORDER BY created_at DESC
                LIMIT 5;
            """)

            print(GREEN + "\n[ INVARIANT FAILURES ]" + RESET)
            print(format_table(risk))

            # -------------------------
            # LIVE SYSTEM METRICS
            # -------------------------
            print(BOLD + "\n[ SYSTEM STATUS ]" + RESET)
            print("Time:", datetime.utcnow().isoformat())
            print("DB:", DB)
            print("Mode: READ-ONLY CONTROL PLANE")
            print("Refresh: 2s")

            time.sleep(2)

        except Exception as e:
            conn.rollback()
            print(RED + "[CONTROL PLANE ERROR]" + RESET, str(e))
            time.sleep(2)

if __name__ == "__main__":
    run()
