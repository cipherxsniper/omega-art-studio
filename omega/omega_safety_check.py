from omega_import_guard import enforce_import_safety
from omega_contracts import validate_call

def run_check():
    enforce_import_safety()
    validate_call("telegram", "orchestrator")
    validate_call("orchestrator", "settlement")
    print("OMEGA SAFETY: OK")

if __name__ == "__main__":
    run_check()
