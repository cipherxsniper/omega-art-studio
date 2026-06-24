#!/usr/bin/env python3

import re
import sys

BLOCKED_PATTERNS = [
    r"UPDATE\s+wallets",
    r"DELETE\s+FROM",
    r"INSERT\s+INTO\s+wallets",
]

def is_safe_sql(query: str) -> bool:
    q = query.upper()
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, q):
            return False
    return True

def gate(query: str):
    if not is_safe_sql(query):
        print("[REJECTED BY CONSENSUS] unsafe mutation detected")
        sys.exit(1)
    print("[CONSENSUS OK]")
    return True

if __name__ == "__main__":
    q = " ".join(sys.argv[1:])
    gate(q)
