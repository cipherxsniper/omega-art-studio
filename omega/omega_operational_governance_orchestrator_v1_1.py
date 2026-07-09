#!/usr/bin/env python3

"""
=========================================================
OMEGA OPERATIONAL GOVERNANCE ORCHESTRATOR v1
Central Governance Arbitration Control Plane
Deterministic Cross-System Decision Engine
=========================================================
"""

import json
import hashlib
import sqlite3
from datetime import datetime, timezone

from omega_env_loader_v1 import get_db_path


# -----------------------------
# HASH ENGINE
# -----------------------------
def hash_obj(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True).encode()
    ).hexdigest()


# -----------------------------
# DB CONNECTION
# -----------------------------
def db():
    return sqlite3.connect(get_db_path())


# -----------------------------
# FETCH SUBSYSTEM STATES
# -----------------------------
def fetch_states(cur):
    try:
        cur.execute("""
            SELECT decision, severity, timestamp
            FROM omega_operational_enforcement_log
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        enforcement = cur.fetchone()
    except Exception:
        enforcement = None

    try:
        cur.execute("""
            SELECT risk_level, risk_score
            FROM financial_risk_assessments
            ORDER BY id DESC
            LIMIT 1
        """)
        risk = cur.fetchone()
    except Exception:
        risk = None

    try:
        cur.execute("""
            SELECT operational_decision, severity, governance_state
            FROM governance_control_plane
            ORDER BY id DESC
            LIMIT 1
        """)
        governance = cur.fetchone()
    except Exception:
        governance = None

    return enforcement, risk, governance


# -----------------------------
# GOVERNANCE ARBITRATION
# -----------------------------
def decide(enforcement, risk, governance):

    freeze_votes = 0

    # enforcement signal
    if enforcement and "ENFORCEMENT_TRIGGERED" in str(enforcement):
        freeze_votes += 1

    # risk signal
    if risk and float(risk[1]) > 0.7:
        freeze_votes += 1

    # governance signal
    if governance and "FREEZE" in str(governance):
        freeze_votes += 2

    if freeze_votes >= 3:
        return "GLOBAL_FREEZE"

    if freeze_votes == 2:
        return "GLOBAL_REVIEW"

    return "GLOBAL_ALLOW"


# -----------------------------
# MAIN RUN
# -----------------------------
def run():
    conn = db()
    cur = conn.cursor()

    enforcement, risk, governance = fetch_states(cur)

    decision = decide(enforcement, risk, governance)

    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "subsystems": {
            "enforcement_present": enforcement is not None,
            "risk_present": risk is not None,
            "governance_present": governance is not None
        },
        "deterministic_hash": hash_obj({
            "decision": decision,
            "enforcement": str(enforcement),
            "risk": str(risk),
            "governance": str(governance)
        })
    }

    print("🏛 OMEGA GOVERNANCE ORCHESTRATOR v1")
    print(json.dumps(output, indent=2))

    conn.close()


if __name__ == "__main__":
    run()
