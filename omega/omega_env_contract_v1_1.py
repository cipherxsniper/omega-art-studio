from typing import Dict
import os

def build_env_contract(raw_env: Dict) -> Dict:
    """
    Normalizes runtime environment for Omega orchestrator.
    Guarantees all required keys exist.
    """

    env = dict(raw_env or {})

    # REQUIRED STRIPE MAPPING SAFETY
    if "STRIPE_SECRET" not in env:
        env["STRIPE_SECRET"] = env.get("STRIPE_SECRET_KEY", "")

    # ENSURE CORE FLAGS
    env.setdefault("env_loaded", True)
    env.setdefault("runtime_mode", "production")

    # SAFETY: prevent None keys
    for k, v in list(env.items()):
        if v is None:
            env[k] = ""

    return env
