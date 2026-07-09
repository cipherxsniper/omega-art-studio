"""
OMEGA DB AUDIT SHADOW LAYER
Logs all DB access in real time
"""

import sqlite3
from datetime import datetime

_original = sqlite3.connect

def audited_connect(db, *args, **kwargs):
    print(f"[DB AUDIT] {datetime.utcnow().isoformat()} -> {db}")
    return _original(db, *args, **kwargs)

sqlite3.connect = audited_connect
