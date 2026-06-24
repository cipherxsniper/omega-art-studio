#!/usr/bin/env python3
import sqlite3
from omega_db_registry import get_db

# OMEGA STANDARD LEDGER CONNECTION (canonical)
conn = sqlite3.connect(get_db("ledger"))

print("[OK] Connected to canonical LEDGER DB")
print("DB:", get_db("ledger"))
