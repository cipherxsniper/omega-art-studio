import json
from uuid import UUID

SYSTEM_ACCOUNT = UUID("00000000-0000-0000-0000-000000000000")

def safe_uuid(val):
    if val is None:
        return None
    if isinstance(val, UUID):
        return str(val)
    return str(val)

def safe_json(val):
    if val is None:
        return {}
    if isinstance(val, str):
        return json.loads(val)
    return val

def safe_account_id(val):
    if val is None:
        return SYSTEM_ACCOUNT
    return val
