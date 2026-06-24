from omega_contracts import validate_call

# Telegram → Orchestrator boundary check
validate_call("telegram", "orchestrator")

# Orchestrator → Settlement boundary check
validate_call("orchestrator", "settlement")
