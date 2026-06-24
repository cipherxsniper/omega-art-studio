#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
OMEGA SPAWN SIGNAL — NODE_SPAWN_SIGNAL PATCH FOR omega_v10.py
═══════════════════════════════════════════════════════════════════════════════
Author:  Thomas Lee Harvey, CEO & Founder — Omega AI / Omega Bank
Date:    June 8, 2026

PURPOSE:
  This is the threshold monitor that makes the network self-growing.
  Wire this into omega_v10.py as a worker that runs every 10 minutes.
  When thresholds are hit, it emits NODE_SPAWN_SIGNAL to omega_ledger.
  Any node watching the DB picks up the signal and bootstraps a new peer.

WIRING INSTRUCTION:
  In omega_v10.py, add SpawnMonitor to the worker list:
    workers = [
        ...existing workers...,
        SpawnMonitor(600),   # Check every 10 minutes
    ]

ENVIRONMENT: Termux Android, Python 3.13, ARM64
             NO pydantic, NO anthropic SDK
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import json
import time
import datetime
import logging

logger = logging.getLogger(__name__)

# ─── SPAWN THRESHOLDS ─────────────────────────────────────────────────────────
SPAWN_THRESHOLDS = {
    "ledger_entries": {
        "value":        1000,
        "description":  "Ledger reached 1,000 entries",
        "cooldown_hours": 24,
    },
    "settled_usd": {
        "value":        10_000.00,
        "description":  "Network settled $10,000+ in transactions",
        "cooldown_hours": 24,
    },
    "active_clients": {
        "value":        10,
        "description":  "10 active paying clients",
        "cooldown_hours": 168,  # once per week max
    },
    "time_epoch": {
        "value":        168,    # hours
        "description":  "Weekly epoch — network heartbeat spawn",
        "cooldown_hours": 168,
    },
}

GENESIS_FILE = "/data/data/com.termux/files/home/omega_genesis.json"

# ─── DB HELPER ────────────────────────────────────────────────────────────────
def _get_db(dbname):
    try:
        import psycopg2
        return psycopg2.connect(
            host="127.0.0.1", port=5432,
            user="postgres", dbname=dbname,
            connect_timeout=8
        )
    except Exception as e:
        logger.warning(f"SpawnMonitor DB connect failed ({dbname}): {e}")
        return None


def _get_genesis_id():
    """Read genesis_id from genesis.json."""
    try:
        if os.path.exists(GENESIS_FILE):
            with open(GENESIS_FILE) as f:
                g = json.load(f)
            return g.get("genesis_id")
    except:
        pass
    return None


# ─── SIGNAL EMITTER ───────────────────────────────────────────────────────────
def emit_spawn_signal(genesis_id, threshold_type, trigger_reason, trigger_value, conn):
    """
    Write a NODE_SPAWN_SIGNAL to omega_spawn_signals.
    Idempotent: checks cooldown before emitting.
    """
    cooldown_hours = SPAWN_THRESHOLDS.get(threshold_type, {}).get("cooldown_hours", 24)
    try:
        cur = conn.cursor()

        # Check cooldown
        cur.execute("""
            SELECT COUNT(*) FROM omega_spawn_signals
            WHERE threshold_type = %s
              AND emitted_at > NOW() - INTERVAL '%s hours'
        """, (threshold_type, cooldown_hours))
        recent = cur.fetchone()[0]

        if recent > 0:
            cur.close()
            return False  # In cooldown

        # Emit signal
        cur.execute("""
            INSERT INTO omega_spawn_signals (
                signal_type, genesis_id, trigger_reason,
                trigger_value, threshold_type, status
            ) VALUES (
                'NODE_SPAWN_SIGNAL', %s, %s, %s, %s, 'pending'
            )
        """, (genesis_id, trigger_reason, trigger_value, threshold_type))
        conn.commit()
        cur.close()

        logger.info(f"⚡ NODE_SPAWN_SIGNAL emitted: {threshold_type} | {trigger_reason}")
        return True

    except Exception as e:
        conn.rollback()
        logger.warning(f"Spawn signal emit failed: {e}")
        return False


# ─── SPAWN MONITOR WORKER ────────────────────────────────────────────────────
class SpawnMonitor:
    """
    Worker that monitors thresholds and emits NODE_SPAWN_SIGNAL.
    Drop-in compatible with omega_v10.py worker pattern.
    Runs every `interval` seconds.
    """

    def __init__(self, interval: int = 600):
        self.interval    = interval
        self.name        = "SpawnMonitor"
        self._last_run   = 0
        self._genesis_id = None
        self._start_time = time.time()

    def _load_genesis_id(self):
        if not self._genesis_id:
            self._genesis_id = _get_genesis_id()
        return self._genesis_id

    def should_run(self):
        return (time.time() - self._last_run) >= self.interval

    def run(self):
        """Check all thresholds, emit signals as needed."""
        self._last_run = time.time()
        genesis_id = self._load_genesis_id()

        if not genesis_id:
            logger.debug("SpawnMonitor: No genesis ID found — skipping")
            return

        conn_ledger = _get_db("omega_ledger")
        conn_bank   = _get_db("omega_bank")

        if not conn_ledger:
            logger.debug("SpawnMonitor: No DB connection — skipping")
            return

        signals_emitted = 0

        try:
            # ── Check 1: Ledger entry count ───────────────────────────────────
            try:
                cur = conn_ledger.cursor()
                cur.execute("SELECT COUNT(*) FROM ledger_entries")
                entry_count = cur.fetchone()[0]
                cur.close()

                threshold = SPAWN_THRESHOLDS["ledger_entries"]["value"]
                if entry_count >= threshold:
                    emitted = emit_spawn_signal(
                        genesis_id, "ledger_entries",
                        f"Ledger reached {entry_count:,} entries",
                        entry_count, conn_ledger
                    )
                    if emitted:
                        signals_emitted += 1
            except Exception as e:
                logger.debug(f"SpawnMonitor ledger check: {e}")

            # ── Check 2: Settled USD ──────────────────────────────────────────
            if conn_bank:
                try:
                    cur = conn_bank.cursor()
                    cur.execute("""
                        SELECT COALESCE(SUM(amount_cents), 0)
                        FROM transactions
                        WHERE status = 'settled'
                    """)
                    settled_cents = cur.fetchone()[0]
                    cur.close()
                    settled_usd = settled_cents / 100.0

                    threshold = SPAWN_THRESHOLDS["settled_usd"]["value"]
                    if settled_usd >= threshold:
                        emitted = emit_spawn_signal(
                            genesis_id, "settled_usd",
                            f"Network settled ${settled_usd:,.2f}",
                            settled_usd, conn_ledger
                        )
                        if emitted:
                            signals_emitted += 1
                except Exception as e:
                    logger.debug(f"SpawnMonitor settled_usd check: {e}")

            # ── Check 3: Active paying clients ────────────────────────────────
            try:
                # Query omega.db via sqlite for active Stripe clients
                import sqlite3
                db_path = "/data/data/com.termux/files/home/omega_runtime/db/omega.db"
                if os.path.exists(db_path):
                    sconn = sqlite3.connect(db_path)
                    sc    = sconn.cursor()
                    sc.execute("""
                        SELECT COUNT(*) FROM leads
                        WHERE status = 'client'
                    """)
                    client_count = sc.fetchone()[0]
                    sconn.close()

                    threshold = SPAWN_THRESHOLDS["active_clients"]["value"]
                    if client_count >= threshold:
                        emitted = emit_spawn_signal(
                            genesis_id, "active_clients",
                            f"{client_count} active paying clients",
                            client_count, conn_ledger
                        )
                        if emitted:
                            signals_emitted += 1
            except Exception as e:
                logger.debug(f"SpawnMonitor client check: {e}")

            # ── Check 4: Weekly epoch ─────────────────────────────────────────
            uptime_hours = (time.time() - self._start_time) / 3600
            if uptime_hours >= SPAWN_THRESHOLDS["time_epoch"]["value"]:
                emitted = emit_spawn_signal(
                    genesis_id, "time_epoch",
                    f"Weekly epoch at {uptime_hours:.1f}h uptime",
                    uptime_hours, conn_ledger
                )
                if emitted:
                    signals_emitted += 1

        finally:
            conn_ledger.close()
            if conn_bank:
                conn_bank.close()

        if signals_emitted:
            logger.info(f"SpawnMonitor: {signals_emitted} signal(s) emitted this cycle")

        return signals_emitted


# ─── STANDALONE CHECK ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    """Run a one-shot threshold check and report."""
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    print()
    print("═" * 60)
    print("  OMEGA SPAWN MONITOR — THRESHOLD CHECK")
    print("═" * 60)

    monitor = SpawnMonitor(interval=0)
    result  = monitor.run()

    print()
    if result:
        print(f"  ⚡ {result} spawn signal(s) emitted")
    else:
        print("  ✅ No thresholds triggered (or cooldown active)")

    print()
    print("  To wire into omega_v10.py, add to workers list:")
    print("    from omega_spawn_signal import SpawnMonitor")
    print("    workers.append(SpawnMonitor(600))")
    print("═" * 60)
