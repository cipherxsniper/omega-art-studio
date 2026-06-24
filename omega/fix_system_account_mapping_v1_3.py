#!/usr/bin/env python3

SYSTEM_ACCOUNT_MAP = {
    "SYSTEM": None  # must never be used directly
}

def resolve_account_id(account_id, cur):
    """
    Enforces UUID-only ledger integrity.
    SYSTEM must resolve to real treasury account.
    """

    if account_id == "SYSTEM":
        cur.execute("""
            SELECT instrument_id
            FROM omega_instruments
            WHERE instrument_type = 'system_account'
            AND metadata->>'name' = 'treasury_system'
            LIMIT 1
        """)
        row = cur.fetchone()
        if not row:
            raise Exception("SYSTEM ACCOUNT NOT INITIALIZED")
        return row[0]

    return account_id
