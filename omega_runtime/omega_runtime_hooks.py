from omega_import_guard import enforce_import_safety
from omega_contracts import validate_call

def bootstrap_telegram():
    enforce_import_safety()
    validate_call("telegram", "orchestrator")

def bootstrap_orchestrator_to_settlement():
    validate_call("orchestrator", "settlement")
