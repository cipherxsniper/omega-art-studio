#!/usr/bin/env python3
"""
OMEGA SCHEMA TRANSLATION LAYER (FIXED - NO RECURSION)
"""

import re
import sqlite3

# SAFE: capture ORIGINAL BEFORE any override
_ORIGINAL_CONNECT = sqlite3.connect

TABLE_MAP = {
    "events": "ledger_events",
    "transactions": "ledger_events",
    "subscriptions": "subscriptions",
    "stripe_events": "stripe_event_log",
}

def translate_sql(query: str) -> str:
    for src, target in TABLE_MAP.items():
        query = re.sub(rf"\b{src}\b", target, query)
    return query


class OmegaCursor:
    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, query, *args, **kwargs):
        translated = translate_sql(query)
        print("[SCHEMA]", query, "→", translated)
        return self.cursor.execute(translated, *args, **kwargs)

    def executemany(self, query, *args, **kwargs):
        translated = translate_sql(query)
        return self.cursor.executemany(translated, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self.cursor, name)


class OmegaConnection:
    def __init__(self, conn):
        self.conn = conn

    def cursor(self):
        return OmegaCursor(self.conn.cursor())

    def execute(self, query, *args, **kwargs):
        translated = translate_sql(query)
        print("[SCHEMA]", query, "→", translated)
        return self.conn.execute(translated, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self.conn, name)


def connect(db_path, *args, **kwargs):
    # CRITICAL FIX: use ORIGINAL connect
    conn = _ORIGINAL_CONNECT(db_path, *args, **kwargs)
    return OmegaConnection(conn)
