#!/usr/bin/env python3
"""
OMEGA STRIPE REALITY PROBE v1 (FIXED)
No NoneType crashes. Deterministic env + DB resolution.
"""

import os
import sqlite3
from omega_env_loader_v1 import get_env, get_db_path


def probe():
    db_path = get_db_path()

    # SAFE stripe checks
    stripe_ready = bool(get_env("STRIPE_SECRET_KEY"))
    webhook_ready = bool(get_env("STRIPE_WEBHOOK_SECRET"))

    # SAFE DB check
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        cur.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1;")
        tables = cur.fetchall()

        db_ok = len(tables) > 0

    except Exception as e:
        db_ok = False

    return {
        "db_path": db_path,
        "stripe_ready": stripe_ready,
        "webhook_ready": webhook_ready,
        "db_ok": db_ok
    }


if __name__ == "__main__":
    print("🧪 OMEGA STRIPE REALITY PROBE v1 (SAFE)")
    print(probe())
