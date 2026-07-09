import os
from pathlib import Path

def bootstrap_env():
    env_path = Path(".env")

    if not env_path.exists():
        raise RuntimeError("Missing .env file")

    # load .env manually (NO dotenv dependency)
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

    # normalize stripe key naming (CRITICAL FIX)
    if "STRIPE_SECRET_KEY" in os.environ and "STRIPE_SECRET" not in os.environ:
        os.environ["STRIPE_SECRET"] = os.environ["STRIPE_SECRET_KEY"]

    required = [
        "STRIPE_SECRET",
        "STRIPE_WEBHOOK_SECRET",
    ]

    missing = [k for k in required if k not in os.environ]

    if missing:
        raise RuntimeError(f"Missing critical env vars: {missing}")

    return dict(os.environ)
