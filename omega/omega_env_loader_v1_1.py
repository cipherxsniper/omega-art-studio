#!/usr/bin/env python3
"""
OMEGA ENV LOADER v1
Deterministic environment resolver for production safety
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# --- deterministic env load (NO find_dotenv) ---
ENV_PATH = Path.home() / "Omega-Production" / "omega_bank" / ".env"
load_dotenv(dotenv_path=ENV_PATH)

def get_env(key: str, default=None):
    value = os.getenv(key)
    return value if value is not None else default


def get_db_path():
    """
    Deterministic DB resolution:
    1. DATABASE_URL (if valid sqlite)
    2. fallback omega_ledger.db
    """
    raw = get_env("DATABASE_URL")

    if raw and isinstance(raw, str) and raw.startswith("sqlite"):
        return raw.replace("sqlite:///", "")

    # SAFE FALLBACK (this is your actual production DB)
    return str(Path.home() / "Omega-Production" / "omega_bank" / "omega_ledger.db")


def env_status():
    return {
        "stripe_secret": bool(get_env("STRIPE_SECRET_KEY")),
        "stripe_webhook": bool(get_env("STRIPE_WEBHOOK_SECRET")),
        "db_configured": bool(get_env("DATABASE_URL")),
        "resolved_db_path": get_db_path()
    }


if __name__ == "__main__":
    print("OMEGA ENV LOADER v1")
    print(env_status())
