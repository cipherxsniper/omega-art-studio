from omega_db_bootstrap_v1 import ensure_db
from omega_env_bootstrap_v1 import bootstrap_env

from omega_event_bus_core_v1 import run as run_event_bus
from omega_ledger_sanitizer_v1 import run as run_sanitizer
from omega_financial_consensus_engine_v1 import run as run_consensus
from omega_settlement_engine_v1 import run as run_settlement

# 🔥 FIX: STRIPE MUST DEPEND ON CONSENSUS, NOT RAW LEDGER
from omega_stripe_binding_layer_v1 import run as run_stripe


def run():
    print("🏦 OMEGA ORCHESTRATOR STARTING")

    ensure_db()
    bootstrap_env()

    # =========================
    # STRICT EXECUTION ORDER
    # =========================

    event_result = run_event_bus()
    run_sanitizer()

    consensus_result = run_consensus()

    run_settlement()

    # 🔥 FIXED: Stripe now runs AFTER consensus
    run_stripe()

    print("✅ PIPELINE COMPLETE")


if __name__ == "__main__":
    run()

# ==============================
# NEXUS DRIFT GUARD HOOK
# ==============================

try:
    from nexus_drift_guard import validate_event

    def nexus_guard(event):
        result = validate_event(event)
        if result.get("nexus_required"):
            print("⚠️ NEXUS ALERT: Drift threshold exceeded")
        return result

except Exception:
    def nexus_guard(event):
        return {"approved": True, "drift_score": 0, "fallback": True}

# ==============================
# NEXUS DRIFT GUARD HOOK
# ==============================

try:
    from nexus_drift_guard import validate_event

    def nexus_guard(event):
        result = validate_event(event)
        if result.get("nexus_required"):
            print("⚠️ NEXUS ALERT: Drift threshold exceeded")
        return result

except Exception:
    def nexus_guard(event):
        return {"approved": True, "drift_score": 0, "fallback": True}

# ==============================
# NEXUS DRIFT GUARD HOOK
# ==============================

try:
    from nexus_drift_guard import validate_event

    def nexus_guard(event):
        result = validate_event(event)
        if result.get("nexus_required"):
            print("⚠️ NEXUS ALERT: Drift threshold exceeded")
        return result

except Exception:
    def nexus_guard(event):
        return {"approved": True, "drift_score": 0, "fallback": True}
