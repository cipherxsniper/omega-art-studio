#!/usr/bin/env python3

import sqlite3
import omega_schema_translate

from omega_db_registry import get_db

print("[OMEGA BOOTSTRAP] Initializing DB routing layer...")

# IMPORTANT: patch using SAFE wrapper (no recursion)
sqlite3.connect = omega_schema_translate.connect

print("[OMEGA BOOTSTRAP] SQLite routing + schema translation ACTIVE")
