#!/usr/bin/env python3
"""
OMEGA ENV SAFE LOADER v1
Deterministic environment resolution layer
Prevents NoneType crashes across Omega system
"""

import os
from pathlib import Path
from dotenv import load_dotenv


# -----------------------------
# LOAD .ENV SAFELY
# -----------------------------
ENV_PATH = Path.home() / "Omega-Production" / "omega_bank" / ".env"
load_dotenv(dotenv_path=ENV_PATH)


# -----------------------------
# SAFE GETTER (NO NONE CRASHES)
# -----------------------------
def get_env(key: str, default=None, required: bool = False):
    value = os.getenv(key)

    if value is None:
        if required:
            raise RuntimeError(f"OMEGA_ENV_MISSING_REQUIRED: {key}")
        return default

    return value


# -----------------------------
# SAFE DATABASE RESOLUTION
# -----------------------------
def get_database_path():
    """
    Deterministic DB resolution:
    Priority:
    1. DATABASE_URL
    2. fallback local sqlite file
    """

    db_url = get_env("DATABASE_URL")

    if db_url:
        return db_url.replace("sqlite:///", "")

    # fallback (critical safety net)
    fallback = ENV_PATH.parent / "omega_ledger.db"
    return str(fallback)


# -----------------------------
# STRIPE SAFE ACCESS
# -----------------------------
def stripe_keys():
    return {
        "secret": get_env("STRIPE_SECRET_KEY", required=True),
        "publishable": get_env("STRIPE_PUBLISHABLE_KEY"),
        "webhook_1": get_env("STRIPE_WEBHOOK_SECRET", required=True),
        "webhook_2": get_env("STRIPE_WEBHOOK_SECRET_2"),
    }


# -----------------------------
# SYSTEM HEALTH CHECK
# -----------------------------
def env_health_check():
    return {
        "stripe_secret": bool(get_env("STRIPE_SECRET_KEY")),
        "stripe_webhook": bool(get_env("STRIPE_WEBHOOK_SECRET")),
        "db_configured": bool(get_env("DATABASE_URL")),
    }


if __name__ == "__main__":
    print("OMEGA ENV SAFE LOADER v1")
    print(env_health_check())
