#!/usr/bin/env python3

import sqlite3
import hashlib
import json
import time

DB = "omega_ledger.db"

conn = sqlite3.connect(DB)

rows = conn.execute("""
SELECT *
FROM ledger_events
ORDER BY id
""").fetchall()

snapshot = {
    "timestamp": time.time(),
    "events": rows
}

blob = json.dumps(snapshot).encode()

digest = hashlib.sha256(blob).hexdigest()

fname = f"omega_snapshot_{int(time.time())}.json"

with open(fname, "w") as f:
    json.dump(snapshot, f)

print("\n=== IMMUTABLE SNAPSHOT COMPLETE ===")
print("FILE :", fname)
print("HASH :", digest)

conn.close()
