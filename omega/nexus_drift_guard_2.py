"""
=========================================================
NEXUS DRIFT GUARD v1 — OMEGA BANK SAFETY LAYER
Ledger-first invariant enforcement + drift detection
NON-INTRUSIVE WRAPPER (does NOT modify core logic)
=========================================================
"""

import time
import hashlib
import json
from dataclasses import dataclass, asdict

CORE_INVARIANT = {
    "ledger_is_source_of_truth": True,
    "single_truth_allowed": True,
    "deterministic_settlement_required": True,
    "no_parallel_financial_states": True
}

def calculate_drift_score(event: dict) -> float:
    score = 0.0

    if event.get("creates_new_state_representation"):
        score += 2.5

    if event.get("duplicates_truth_layer"):
        score += 2.0

    if event.get("affects_settlement_determinism") is False:
        score += 1.0

    if event.get("adds_orchestration_layer"):
        score += 1.5

    if len(str(event)) > 500:
        score += 0.5

    return round(score, 3)


def invariant_gates(event: dict) -> dict:
    violations = []

    if event.get("touches_non_ledger_truth"):
        violations.append("NON_LEDGER_TRUTH_MODIFICATION")

    if event.get("introduces_parallel_state"):
        violations.append("PARALLEL_STATE_DETECTED")

    if event.get("breaks_determinism"):
        violations.append("NON_DETERMINISTIC_BEHAVIOR")

    if event.get("orphan_module"):
        violations.append("ORPHAN_MODULE_NO_LEDGER_LINK")

    return {
        "approved": len(violations) == 0,
        "violations": violations
    }


def validate_execution_path(event: dict) -> bool:
    required_chain = ["event", "decision", "state_change", "ledger_update"]
    path = event.get("execution_path", [])
    return all(step in path for step in required_chain)


def nexus_snapshot(system_state: dict) -> dict:
    snapshot = {
        "timestamp": time.time(),
        "goal_state": system_state.get("goal_state"),
        "execution_state": system_state.get("execution_state"),
        "modules": system_state.get("modules", []),
        "drift_report": [],
        "actions": {"keep": [], "merge": [], "delete": [], "defer": []}
    }

    for module in snapshot["modules"]:
        score = calculate_drift_score(module)

        if score < 1.5:
            snapshot["actions"]["keep"].append(module.get("name"))
        elif score < 3.0:
            snapshot["actions"]["defer"].append(module.get("name"))
        else:
            snapshot["actions"]["delete"].append(module.get("name"))

        snapshot["drift_report"].append({
            "module": module.get("name"),
            "drift_score": score
        })

    return snapshot


def validate_event(event: dict) -> dict:
    gate_result = invariant_gates(event)
    drift_score = calculate_drift_score(event)
    execution_valid = validate_execution_path(event)

    return {
        "approved": gate_result["approved"] and execution_valid,
        "drift_score": drift_score,
        "execution_valid": execution_valid,
        "violations": gate_result["violations"],
        "nexus_required": drift_score > 2.0
    }


def hash_event(event: dict) -> str:
    return hashlib.sha256(
        json.dumps(event, sort_keys=True).encode()
    ).hexdigest()
