#!/usr/bin/env python3
"""
OMEGA DB GLOBAL OVERRIDE LAYER
Forces all sqlite3.connect() calls through registry routing logic.
"""

import sqlite3
from omega_db_registry import get_db

_original_connect = sqlite3.connect

def routed_connect(database, *args, **kwargs):
    """
    Intercepts all DB connections and routes them through Omega registry.
    """

    # ROUTING RULES (edit safely if needed)
    if database in ("ledger", "omega_ledger.db"):
        database = get_db("ledger")

    elif database in ("billing", "billing.db"):
        database = get_db("billing")

    elif database in ("bank", "omega_bank.db"):
        database = get_db("bank")

    elif database in ("users", "omega_users.db"):
        database = get_db("users")

    elif database in ("queue", "event_queue.db"):
        database = get_db("queue")

    elif database in ("idempotency", "idempotency.db"):
        database = get_db("idempotency")

    elif database in ("external", "external_accounts.db"):
        database = get_db("external")

    # default passthrough (unknown DBs still allowed)
    return _original_connect(database, *args, **kwargs)

# APPLY PATCH (global monkey patch)
sqlite3.connect = routed_connect

print("[OMEGA] SQLite global override ACTIVE")
