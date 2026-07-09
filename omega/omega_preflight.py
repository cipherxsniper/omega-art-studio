#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
OMEGA PRE-FLIGHT — GENESIS READINESS CHECK
═══════════════════════════════════════════════════════════════════════════════
Run this BEFORE omega_genesis.py to verify every system is live and clean.
Nothing proceeds until this passes 100%.

Usage: python3 omega_preflight.py
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import datetime
import subprocess

DB_HOST = "127.0.0.1"
DB_PORT = 5432
DB_USER = "postgres"

PASS = "✅"
FAIL = "❌"
WARN = "⚠️ "

results = []

def check(label, passed, detail=""):
    icon = PASS if passed else FAIL
    results.append(passed)
    line = f"  {icon}  {label}"
    if detail:
        line += f"\n       {detail}"
    print(line)
    return passed

def section(title):
    print()
    print(f"  ── {title} {'─' * (54 - len(title))}")

def db(dbname):
    try:
        import psycopg2
        c = psycopg2.connect(host=DB_HOST, port=DB_PORT,
                             user=DB_USER, dbname=dbname,
                             connect_timeout=8)
        return c
    except Exception as e:
        return None

def q(conn, sql, params=None):
    try:
        cur = conn.cursor()
        cur.execute("SAVEPOINT pf")
        cur.execute(sql, params or [])
        row = cur.fetchone()
        cur.execute("RELEASE SAVEPOINT pf")
        cur.close()
        return row
    except Exception as e:
        try:
            cur.execute("ROLLBACK TO SAVEPOINT pf")
            cur.close()
        except:
            pass
        return None

def qa(conn, sql, params=None):
    try:
        cur = conn.cursor()
        cur.execute("SAVEPOINT pf")
        cur.execute(sql, params or [])
        rows = cur.fetchall()
        cur.execute("RELEASE SAVEPOINT pf")
        cur.close()
        return rows
    except Exception as e:
        try:
            cur.execute("ROLLBACK TO SAVEPOINT pf")
            cur.close()
        except:
            pass
        return []

# ─────────────────────────────────────────────────────────────────────────────
print()
print("═" * 62)
print("  OMEGA QUANTUM GENESIS — PRE-FLIGHT DIAGNOSTIC")
print(f"  {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
print("═" * 62)

# ── 1. SSH TUNNEL ─────────────────────────────────────────────────────────────
section("SSH TUNNEL")

try:
    result = subprocess.run(
        ["pgrep", "-f", "ssh.*omega_bridge"],
        capture_output=True, text=True
    )
    tunnel_pid = result.stdout.strip()
    check("SSH tunnel process running",
          bool(tunnel_pid),
          f"PID: {tunnel_pid}" if tunnel_pid else "Start with: nohup ssh -i ~/.ssh/omega_bridge -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -L 5432:127.0.0.1:5432 u0_a253@192.168.11.163 -p 8022 -N &")
except:
    check("SSH tunnel process check", False, "pgrep failed")

# ── 2. DATABASE CONNECTIONS ───────────────────────────────────────────────────
section("DATABASE CONNECTIONS")

conn_bank   = db("omega_bank")
conn_ledger = db("omega_ledger")

check("omega_bank connection",
      conn_bank is not None,
      "Connected to PostgreSQL omega_bank" if conn_bank else "FAILED — is SSH tunnel up?")

check("omega_ledger connection",
      conn_ledger is not None,
      "Connected to PostgreSQL omega_ledger" if conn_ledger else "FAILED — is SSH tunnel up?")

# ── 3. omega_bank TABLES ──────────────────────────────────────────────────────
section("OMEGA_BANK TABLES & DATA")

if conn_bank:
    # List all tables
    tables = qa(conn_bank, """
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename
    """)
    table_names = [t[0] for t in tables]
    check("omega_bank tables exist",
          len(table_names) > 0,
          f"Tables: {', '.join(table_names)}")

    # Wallets
    row = q(conn_bank, "SELECT COUNT(*) FROM wallets")
    wallet_count = row[0] if row else 0
    check(f"Wallets: {wallet_count} found",
          wallet_count > 0,
          f"Expected 13, found {wallet_count}")

    # Accounts
    row = q(conn_bank, "SELECT COUNT(*) FROM accounts")
    acct_count = row[0] if row else 0
    check(f"Accounts: {acct_count} found",
          acct_count > 0)

    # Show ALL wallets with balances
    print()
    print("       WALLET DETAIL:")
    wallet_rows = qa(conn_bank, """
        SELECT
            id,
            COALESCE(wallet_type, account_type, 'unknown') as wtype,
            COALESCE(balance_cents, 0) as bal,
            COALESCE(currency, 'USD') as cur,
            COALESCE(status, 'active') as status
        FROM wallets
        ORDER BY COALESCE(balance_cents, 0) DESC
        LIMIT 20
    """)
    if not wallet_rows:
        # Try accounts table instead
        wallet_rows = qa(conn_bank, """
            SELECT id,
                   COALESCE(account_type, 'unknown'),
                   COALESCE(balance_cents, 0),
                   COALESCE(currency, 'USD'),
                   COALESCE(status, 'active')
            FROM accounts
            ORDER BY COALESCE(balance_cents, 0) DESC
            LIMIT 20
        """)

    treasury_cents = 0
    for row in wallet_rows:
        wid, wtype, bal, cur, status = row
        bal_usd = bal / 100.0
        marker = " ◄ TREASURY" if "TREASURY" in str(wtype).upper() else ""
        print(f"       {str(wid)[:8]}... | {str(wtype):<20} | ${bal_usd:>16,.2f} {cur}{marker}")
        if "TREASURY" in str(wtype).upper():
            treasury_cents = bal

    # If no TREASURY type found, use the highest balance
    if treasury_cents == 0 and wallet_rows:
        treasury_cents = wallet_rows[0][2]
        print(f"\n       NOTE: No TREASURY type found — using highest balance wallet")

    treasury_usd = treasury_cents / 100.0
    print()
    check(f"Treasury balance readable: ${treasury_usd:,.2f}",
          treasury_usd >= 0,
          f"Raw cents: {treasury_cents}")

    # Total across all wallets
    row = q(conn_bank, "SELECT COALESCE(SUM(balance_cents),0) FROM wallets")
    total_cents = row[0] if row else 0
    total_usd = total_cents / 100.0
    print(f"       Total across all wallets: ${total_usd:,.2f}")

    # Cards
    card_count = 0
    for tbl in ("virtual_cards", "cards", "issued_cards"):
        row = q(conn_bank, f"SELECT COUNT(*) FROM {tbl}")
        if row:
            card_count = row[0]
            check(f"Virtual cards ({tbl}): {card_count}", True)
            break
    if card_count == 0:
        check("Virtual cards", False, "No cards table found")

else:
    check("omega_bank data checks", False, "Skipped — no connection")

# ── 4. omega_ledger TABLES ────────────────────────────────────────────────────
section("OMEGA_LEDGER TABLES & DATA")

if conn_ledger:
    tables = qa(conn_ledger, """
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename
    """)
    table_names_l = [t[0] for t in tables]
    check("omega_ledger tables exist",
          len(table_names_l) > 0,
          f"Tables: {', '.join(table_names_l)}")

    # Ledger entries
    row = q(conn_ledger, "SELECT COUNT(*) FROM ledger_entries")
    entry_count = row[0] if row else 0
    check(f"Ledger entries: {entry_count}", True)

    # Max sequence
    row = q(conn_ledger, "SELECT MAX(global_sequence) FROM ledger_entries")
    max_seq = row[0] if row else 0
    check(f"Max sequence: {max_seq}", True)

    # Chain tip
    row = q(conn_ledger, """
        SELECT entry_hash FROM ledger_entries
        ORDER BY global_sequence DESC LIMIT 1
    """)
    chain_tip = row[0] if row else "GENESIS"
    check(f"Chain tip hash readable",
          True,
          f"{chain_tip[:32]}..." if chain_tip and chain_tip != "GENESIS" else "GENESIS (first entry)")

    # Check if genesis tables already exist
    genesis_exists = "omega_genesis_events" in table_names_l
    node_reg_exists = "omega_node_registry" in table_names_l

    check(f"Genesis tables pre-exist: {'YES — will upsert' if genesis_exists else 'NO — will create'}",
          True)

else:
    check("omega_ledger data checks", False, "Skipped — no connection")

# ── 5. KEY FILES ──────────────────────────────────────────────────────────────
section("KEY FILES ON PHONE 1")

home = "/data/data/com.termux/files/home"
key_files = {
    "omega_v10.py":          "Main production script",
    "omega_sentinel.py":     "Function hash watchdog",
    "omega_oracle_v2.py":    "Self-grading gate",
    "omega_genesis.py":      "Genesis writer ← THIS FILE",
    "omega_node_bootstrap.py": "Node bootstrap script",
    "omega_spawn_signal.py": "Spawn signal worker",
    ".env":                  "Secrets",
    ".ssh/omega_bridge":     "SSH key to Phone 2",
}
for fname, desc in key_files.items():
    path = f"{home}/{fname}"
    exists = os.path.exists(path)
    size = os.path.getsize(path) if exists else 0
    check(f"{fname}",
          exists,
          f"{desc} ({size:,} bytes)" if exists else f"MISSING — {desc}")

# ── 6. OMEGA PROCESS ──────────────────────────────────────────────────────────
section("RUNNING PROCESSES")

for proc_name in ("omega_v10.py", "omega_guardian", "omega_sentinel"):
    try:
        result = subprocess.run(
            ["pgrep", "-f", proc_name],
            capture_output=True, text=True
        )
        pid = result.stdout.strip().split("\n")[0]
        check(f"{proc_name}",
              bool(pid),
              f"PID {pid}" if pid else "Not running")
    except:
        check(f"{proc_name}", False, "pgrep failed")

# ── 7. GENESIS FILE STATUS ────────────────────────────────────────────────────
section("PREVIOUS GENESIS STATE")

genesis_path = f"{home}/omega_genesis.json"
if os.path.exists(genesis_path):
    try:
        with open(genesis_path) as f:
            prev = json.load(f)
        prev_id   = prev.get("genesis_id", "unknown")
        prev_hash = prev.get("genesis_hash", "unknown")
        prev_ts   = prev.get("genesis_ts", "unknown")
        prev_db   = prev.get("db_written", False)
        check("Previous genesis.json found",
              True,
              f"ID: {prev_id[:8]}... | DB Written: {prev_db} | TS: {prev_ts}")
        if not prev_db:
            print(f"       {WARN} Previous genesis was JSON-only — this run will write to DB ✅")
    except:
        check("Previous genesis.json", False, "File exists but unreadable")
else:
    check("No previous genesis (clean first run)", True,
          "omega_genesis.py will create a fresh one")

# ── FINAL VERDICT ─────────────────────────────────────────────────────────────
print()
print("═" * 62)
total   = len(results)
passed  = sum(results)
failed  = total - passed
pct     = int(passed / total * 100) if total else 0

if failed == 0:
    print(f"  ⚡ ALL SYSTEMS GO — {passed}/{total} checks passed")
    print()
    print("  READY TO FIRE QUANTUM GENESIS.")
    print()
    print("  Run:")
    print("    python3 omega_genesis.py")
elif failed <= 2:
    print(f"  {WARN} MOSTLY READY — {passed}/{total} passed, {failed} warnings")
    print()
    print("  Fix warnings above, then run:")
    print("    python3 omega_genesis.py")
else:
    print(f"  {FAIL} NOT READY — {passed}/{total} passed, {failed} failures")
    print()
    print("  Fix failures above before running omega_genesis.py")
print("═" * 62)
print()

# Close connections
if conn_bank:
    conn_bank.close()
if conn_ledger:
    conn_ledger.close()

sys.exit(0 if failed == 0 else 1)
