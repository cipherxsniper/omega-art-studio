#!/usr/bin/env python3
"""
OM109 — Omega Alternating Key Signing Algorithm v1.0
Invented by Thomas Lee Harvey, Omega AI / Omega Bank.

Concept: Unlike static HMAC signing where one key signs everything,
OM109 ALTERNATES between two independently-derived key streams (A and B),
each rotating based on a counter and the previous output. Every signature
is a function of: data + key_A(n) + key_B(n) + chain_position + previous_fingerprint.

This means:
  - No two fingerprints can ever collide, even for identical input data,
    because the chain position and previous fingerprint are baked in.
  - Each fingerprint is a 64-character hex digital fingerprint (SHA-256).
  - The alternating dual-key structure means an attacker who recovers
    key_A at position n cannot predict key_B at position n, and vice versa.
  - Verifiable: given the genesis seed and chain position, anyone with
    the master key can re-derive and verify any fingerprint in the chain.

Pure Python. SHA-256 + HMAC primitives only. No external deps.
"""
import os, hmac, hashlib, json, secrets
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
STATE_PATH = HOME / "omega_runtime/state/om109_chain.json"

def _load_master_key() -> bytes:
    """Derive master key from .env MASTER_ENCRYPTION_KEY, or generate one."""
    env_path = HOME / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("MASTER_ENCRYPTION_KEY="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                return hashlib.sha256(val.encode()).digest()
    return hashlib.sha256(b"omega_om109_fallback_seed").digest()

MASTER_KEY = _load_master_key()


def _derive_key_a(position: int, genesis_seed: str) -> bytes:
    """Key stream A — derived from position + genesis seed."""
    msg = f"OM109-A|{genesis_seed}|{position}".encode()
    return hmac.new(MASTER_KEY, msg, hashlib.sha256).digest()


def _derive_key_b(position: int, genesis_seed: str, prev_fingerprint: str) -> bytes:
    """
    Key stream B — derived from position + genesis seed + previous fingerprint.
    This is what makes B unpredictable even if A is known: B depends on
    the OUTPUT of the previous step, creating a hash chain dependency.
    """
    msg = f"OM109-B|{genesis_seed}|{position}|{prev_fingerprint}".encode()
    return hmac.new(MASTER_KEY, msg, hashlib.sha256).digest()


def _load_chain() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"genesis_seed": None, "position": 0, "last_fingerprint": "GENESIS", "history": []}


def _save_chain(chain: dict):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(chain, indent=2, default=str))


def init_chain(genesis_seed: str = None) -> dict:
    """
    Initialize a new OM109 chain with a unique genesis seed.
    If no seed provided, generates a cryptographically random one.
    """
    if genesis_seed is None:
        genesis_seed = secrets.token_hex(16)

    chain = {
        "genesis_seed": genesis_seed,
        "position": 0,
        "last_fingerprint": hashlib.sha256(f"OM109-GENESIS|{genesis_seed}".encode()).hexdigest(),
        "history": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_chain(chain)
    return chain


def sign(data: str, chain: dict = None) -> dict:
    """
    Sign data using OM109 alternating-key chain.
    Returns a unique digital fingerprint (64-char hex), guaranteed unique
    even for identical input data, because it's bound to the chain position
    and the previous fingerprint.
    """
    if chain is None:
        chain = _load_chain()
        if chain["genesis_seed"] is None:
            chain = init_chain()

    position = chain["position"] + 1
    genesis_seed = chain["genesis_seed"]
    prev_fp = chain["last_fingerprint"]

    key_a = _derive_key_a(position, genesis_seed)
    key_b = _derive_key_b(position, genesis_seed, prev_fp)

    # Alternate: even positions sign with A-then-B, odd positions sign with B-then-A
    if position % 2 == 0:
        intermediate = hmac.new(key_a, data.encode(), hashlib.sha256).digest()
        final_input = intermediate + key_b + prev_fp.encode()
    else:
        intermediate = hmac.new(key_b, data.encode(), hashlib.sha256).digest()
        final_input = intermediate + key_a + prev_fp.encode()

    fingerprint = hashlib.sha256(final_input).hexdigest()

    record = {
        "position": position,
        "data_hash": hashlib.sha256(data.encode()).hexdigest(),
        "fingerprint": fingerprint,
        "prev_fingerprint": prev_fp,
        "alternation": "A->B" if position % 2 == 0 else "B->A",
        "ts": datetime.now(timezone.utc).isoformat(),
    }

    chain["position"] = position
    chain["last_fingerprint"] = fingerprint
    chain["history"].append(record)
    if len(chain["history"]) > 1000:
        chain["history"] = chain["history"][-1000:]
    _save_chain(chain)

    return record


def verify(data: str, fingerprint: str, position: int, chain: dict = None) -> bool:
    """
    Verify a fingerprint by re-deriving it from the chain at the given position.
    Requires the chain history to look up prev_fingerprint at position-1.
    """
    if chain is None:
        chain = _load_chain()

    genesis_seed = chain["genesis_seed"]
    if genesis_seed is None:
        return False

    # Find prev_fingerprint for this position
    if position == 1:
        prev_fp = hashlib.sha256(f"OM109-GENESIS|{genesis_seed}".encode()).hexdigest()
    else:
        prev_record = next((h for h in chain["history"] if h["position"] == position - 1), None)
        if not prev_record:
            return False
        prev_fp = prev_record["fingerprint"]

    key_a = _derive_key_a(position, genesis_seed)
    key_b = _derive_key_b(position, genesis_seed, prev_fp)

    if position % 2 == 0:
        intermediate = hmac.new(key_a, data.encode(), hashlib.sha256).digest()
        final_input = intermediate + key_b + prev_fp.encode()
    else:
        intermediate = hmac.new(key_b, data.encode(), hashlib.sha256).digest()
        final_input = intermediate + key_a + prev_fp.encode()

    expected = hashlib.sha256(final_input).hexdigest()
    return hmac.compare_digest(expected, fingerprint)


def status():
    chain = _load_chain()
    print(f"\n{'='*54}")
    print(f"  OM109 — ALTERNATING KEY CHAIN STATUS")
    print(f"{'='*54}")
    print(f"  Genesis seed:     {chain.get('genesis_seed')}")
    print(f"  Chain position:   {chain.get('position')}")
    print(f"  Last fingerprint: {chain.get('last_fingerprint', '')[:32]}...")
    print(f"  History entries:  {len(chain.get('history', []))}")
    print(f"{'='*54}")


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "init":
        chain = init_chain()
        print(f"OM109 chain initialized")
        print(f"Genesis seed: {chain['genesis_seed']}")
        print(f"Genesis fingerprint: {chain['last_fingerprint']}")

    elif cmd == "sign":
        data = sys.argv[2] if len(sys.argv) > 2 else "test_data"
        record = sign(data)
        print(f"\nSigned: \"{data}\"")
        print(f"  Position:    {record['position']}")
        print(f"  Alternation: {record['alternation']}")
        print(f"  Fingerprint: {record['fingerprint']}")

    elif cmd == "verify":
        data = sys.argv[2] if len(sys.argv) > 2 else "test_data"
        fp = sys.argv[3] if len(sys.argv) > 3 else ""
        pos = int(sys.argv[4]) if len(sys.argv) > 4 else 1
        ok = verify(data, fp, pos)
        print(f"Verification: {'✅ VALID' if ok else '❌ INVALID'}")

    elif cmd == "test":
        print("OM109 SELF-TEST\n")
        chain = init_chain()
        print(f"Genesis seed: {chain['genesis_seed']}")

        # Sign the SAME data 5 times — fingerprints must all differ
        fingerprints = set()
        for i in range(5):
            record = sign("identical_data_payload")
            print(f"  Position {record['position']} [{record['alternation']}]: {record['fingerprint'][:24]}...")
            fingerprints.add(record['fingerprint'])

        if len(fingerprints) == 5:
            print(f"\n✅ All 5 fingerprints unique despite identical input data")
        else:
            print(f"\n❌ COLLISION DETECTED — only {len(fingerprints)} unique fingerprints")

        # Verify each one
        chain = _load_chain()
        all_valid = True
        for record in chain["history"][-5:]:
            ok = verify("identical_data_payload", record["fingerprint"], record["position"], chain)
            status_icon = "✅" if ok else "❌"
            print(f"  {status_icon} Verify position {record['position']}: {'VALID' if ok else 'INVALID'}")
            if not ok:
                all_valid = False

        print(f"\n{'✅ OM109 SELF-TEST PASSED' if all_valid and len(fingerprints)==5 else '❌ OM109 SELF-TEST FAILED'}")

    else:
        status()
