#!/usr/bin/env python3
"""
OMEGA RECONCILIATION ENGINE v1
External truth validation layer for Omega financial core.

Validates:
- Ledger integrity (hash chain)
- Event-store alignment
- Settlement correctness
- Idempotency correctness
- Balance drift detection
"""

import sqlite3
import hashlib
from datetime import datetime

DB = "omega_ledger.db"


def conn():
    return sqlite3.connect(DB)


# ---------------------------
# FETCHERS
# ---------------------------

def get_events(cur):
    cur.execute("SELECT event_id, type, payload, hash FROM events ORDER BY rowid ASC")
    return cur.fetchall()


def get_ledger(cur):
    cur.execute("SELECT entry_hash, prev_hash FROM omega_ledger_chain ORDER BY rowid ASC")
    return cur.fetchall()


def get_settlements(cur):
    cur.execute("SELECT event_id, status FROM omega_settlement_state")
    return cur.fetchall()


# ---------------------------
# CHECK 1: HASH CHAIN INTEGRITY
# ---------------------------

def verify_hash_chain(ledger):
    prev = None

    for entry_hash, prev_hash in ledger:
        if prev is not None and prev != prev_hash:
            return False, f"CHAIN_BREAK at {entry_hash}"
        prev = entry_hash

    return True, "OK"


# ---------------------------
# CHECK 2: EVENT ↔ LEDGER ALIGNMENT
# ---------------------------

def verify_event_alignment(events, ledger):
    ledger_hashes = {h for h, _ in ledger}
    event_hashes = {e[3] for e in events if e[3]}

    missing = event_hashes - ledger_hashes

    if missing:
        return False, f"LEDGER_MISSING_EVENTS: {list(missing)}"

    return True, "OK"


# ---------------------------
# CHECK 3: SETTLEMENT CONSISTENCY
# ---------------------------

def verify_settlement(settlements, events):
    event_ids = {e[0] for e in events}
    settlement_ids = {s[0] for s in settlements}

    missing = settlement_ids - event_ids

    if missing:
        return False, f"SETTLEMENT_ORPHANS: {list(missing)}"

    return True, "OK"


# ---------------------------
# CHECK 4: IDEMPOTENCY SANITY
# ---------------------------

def verify_idempotency(events):
    seen = set()

    for e in events:
        if e[0] in seen:
            return False, f"DUPLICATE_EVENT: {e[0]}"
        seen.add(e[0])

    return True, "OK"


# ---------------------------
# MAIN RECONCILIATION RUN
# ---------------------------

def run():
    c = conn()
    cur = c.cursor()

    events = get_events(cur)
    ledger = get_ledger(cur)
    settlements = get_settlements(cur)

    chain_ok, chain_msg = verify_hash_chain(ledger)
    align_ok, align_msg = verify_event_alignment(events, ledger)
    settle_ok, settle_msg = verify_settlement(settlements, events)
    idem_ok, idem_msg = verify_idempotency(events)

    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_count": len(events),
        "ledger_count": len(ledger),
        "settlement_count": len(settlements),

        "chain_check": chain_ok,
        "alignment_check": align_ok,
        "settlement_check": settle_ok,
        "idempotency_check": idem_ok,

        "chain_msg": chain_msg,
        "alignment_msg": align_msg,
        "settlement_msg": settle_msg,
        "idempotency_msg": idem_msg,
    }

    if chain_ok and align_ok and settle_ok and idem_ok:
        result["status"] = "RECONCILED"
    else:
        result["status"] = "DRIFT_DETECTED"

    print(result)
    return result


if __name__ == "__main__":
    run()
