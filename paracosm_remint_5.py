#!/usr/bin/env python3
"""Re-mint exactly 5 missing Paracosm tokens: 1004, 1010, 1013, 1014, 1024"""
import sys
sys.path.insert(0, '/data/data/com.termux/files/home')

# Import everything from the engine
from paracosm_engine import (
    mint_token, IMPOSSIBLE_TOKENS
)

MISSING = [1004, 1010, 1013, 1014, 1024]

print(f"\n{'═'*52}")
print(f"  PARACOSM — Re-minting {len(MISSING)} missing tokens")
print(f"  Tokens: {MISSING}")
print(f"  Impossible tokens in collection: {IMPOSSIBLE_TOKENS}")
print(f"{'═'*52}\n")

success = []
failed = []

for token_id in MISSING:
    ok = mint_token(token_id)
    if ok:
        success.append(token_id)
    else:
        failed.append(token_id)

print(f"\n{'═'*52}")
print(f"  Done — {len(success)} succeeded, {len(failed)} failed")
if failed:
    print(f"  Failed: {failed}")
print(f"{'═'*52}\n")
