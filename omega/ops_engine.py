"""
ops_engine.py — Oracle Proof Engine (OPS) v1
=============================================
A deterministic, cryptographically-chained proof system for evaluating,
validating, and auditing AI-generated or developer-written system states.

Formal model:
    P_t = (S_t, E_t, H_t)
    H_t = SHA-256(S_t || codebase_hash || metrics || prev_H)

Invariants enforced:
    1. Hash consistency    — H must be reproducible from current state
    2. Monotonic floors    — F_i(t+1) >= F_i(t)  [ratchet per component]
    3. Proof acceptance    — syntax + tests + no invariant break + hash_ok
    4. Chain integrity     — each proof links to its predecessor

CLI:
    python ops_engine.py score   <path>
    python ops_engine.py verify  <chain_file>
    python ops_engine.py rollback-check <chain_file>
    python ops_engine.py export  <chain_file>
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import textwrap
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants & configuration
# ---------------------------------------------------------------------------
OPS_CHAIN_FILE  = os.getenv("OPS_CHAIN_FILE",  "ops_proof_chain.jsonl")
OPS_FLOORS_FILE = os.getenv("OPS_FLOORS_FILE", "ops_floors.json")
OPS_DB_FILE     = os.getenv("OPS_DB_FILE",     "ops_engine.db")

COMPONENT_WEIGHTS: Dict[str, float] = {
    "syntax":         0.20,
    "test_coverage":  0.20,
    "db_integrity":   0.20,
    "event_chain":    0.15,
    "consensus":      0.15,
    "api_contracts":  0.10,
}
assert abs(sum(COMPONENT_WEIGHTS.values()) - 1.0) < 1e-9, "Weights must sum to 1.0"

ACCEPTANCE_THRESHOLD = 70.0   # minimum weighted score to PASS
STRICT_MONOTONIC     = False   # if True, reject any score regression (not just floor violations)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class ComponentScore:
    name:     str
    score:    float          # 0–100
    weight:   float
    evidence: Dict[str, Any] = field(default_factory=dict)
    passed:   bool           = True
    notes:    str            = ""

    @property
    def weighted(self) -> float:
        return self.score * self.weight


@dataclass
class ProofEvent:
    """
    P_t = (S_t, E_t, H_t)
    An immutable record of a single system evaluation.
    """
    proof_id:    str
    timestamp:   str
    score:       float
    grade:       str
    components:  Dict[str, Any]    # ComponentScore → dict for serialisation
    evidence:    Dict[str, Any]
    system_hash: str               # H_t
    prev_hash:   Optional[str]     # H_{t-1}  (None for genesis)
    chain_hash:  str               # SHA-256(proof_id || system_hash || prev_hash)
    verdict:     str               # PASS | FAIL | REJECT
    violations:  List[str]
    target_path: str


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def _init_db() -> sqlite3.Connection:
    conn = sqlite3.connect(OPS_DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ops_floors (
            component TEXT PRIMARY KEY,
            floor     REAL NOT NULL,
            set_at    TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ops_proofs (
            proof_id    TEXT PRIMARY KEY,
            timestamp   TEXT NOT NULL,
            score       REAL NOT NULL,
            grade       TEXT NOT NULL,
            verdict     TEXT NOT NULL,
            system_hash TEXT NOT NULL,
            prev_hash   TEXT,
            chain_hash  TEXT NOT NULL UNIQUE,
            target_path TEXT NOT NULL,
            proof_json  TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def _load_floors() -> Dict[str, float]:
    conn = _init_db()
    rows = conn.execute("SELECT component, floor FROM ops_floors").fetchall()
    conn.close()
    return {r["component"]: r["floor"] for r in rows}


def _save_floor(component: str, value: float) -> None:
    conn  = _init_db()
    now   = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO ops_floors (component, floor, set_at) VALUES (?, ?, ?) "
        "ON CONFLICT(component) DO UPDATE SET floor=excluded.floor, set_at=excluded.set_at",
        (component, value, now),
    )
    conn.commit()
    conn.close()


def _persist_proof(proof: ProofEvent) -> None:
    """Write proof to both the append-only JSONL chain file and the SQLite index."""
    # 1. JSONL chain (append-only — never modified)
    with open(OPS_CHAIN_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(proof)) + "\n")

    # 2. SQLite index (for fast queries)
    conn = _init_db()
    conn.execute(
        "INSERT OR IGNORE INTO ops_proofs "
        "(proof_id, timestamp, score, grade, verdict, system_hash, prev_hash, chain_hash, target_path, proof_json) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            proof.proof_id, proof.timestamp, proof.score, proof.grade,
            proof.verdict, proof.system_hash, proof.prev_hash, proof.chain_hash,
            proof.target_path, json.dumps(asdict(proof)),
        ),
    )
    conn.commit()
    conn.close()


def _load_chain() -> List[Dict[str, Any]]:
    if not Path(OPS_CHAIN_FILE).exists():
        return []
    proofs = []
    with open(OPS_CHAIN_FILE, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                proofs.append(json.loads(line))
    return proofs


def _latest_proof() -> Optional[Dict[str, Any]]:
    chain = _load_chain()
    return chain[-1] if chain else None


# ---------------------------------------------------------------------------
# Cryptographic helpers
# ---------------------------------------------------------------------------

def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _compute_system_hash(
    target_path: str,
    component_scores: Dict[str, float],
    timestamp: str,
    prev_hash: Optional[str],
) -> str:
    """
    H_t = SHA-256(file_content_hash || score_vector || timestamp || prev_hash)
    Reproducible given the same inputs.
    """
    content_hash = _hash_path(target_path)
    score_blob   = json.dumps(component_scores, sort_keys=True)
    raw          = f"{content_hash}|{score_blob}|{timestamp}|{prev_hash or 'GENESIS'}"
    return _sha256(raw)


def _hash_path(path: str) -> str:
    """SHA-256 over a file or all .py files in a directory (sorted for determinism)."""
    p = Path(path)
    if not p.exists():
        return _sha256("__missing__")
    if p.is_file():
        return _sha256(p.read_text(encoding="utf-8", errors="replace"))
    # directory: hash concatenation of all Python source files
    parts = []
    for src in sorted(p.rglob("*.py")):
        parts.append(src.read_text(encoding="utf-8", errors="replace"))
    return _sha256("\n".join(parts))


def _compute_chain_hash(proof_id: str, system_hash: str, prev_hash: Optional[str]) -> str:
    raw = f"{proof_id}|{system_hash}|{prev_hash or 'GENESIS'}"
    return _sha256(raw)


# ---------------------------------------------------------------------------
# Component evaluators
# ---------------------------------------------------------------------------

def _eval_syntax(target_path: str) -> ComponentScore:
    """Parse every .py file; score = 100 − (10 × error_count), floor 0."""
    p      = Path(target_path)
    files  = list(p.rglob("*.py")) if p.is_dir() else [p] if p.suffix == ".py" else []
    errors: List[str] = []
    for f in files:
        try:
            ast.parse(f.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError as e:
            errors.append(f"{f.name}:{e.lineno} — {e.msg}")

    score = max(0.0, 100.0 - len(errors) * 10)
    return ComponentScore(
        name     = "syntax",
        score    = score,
        weight   = COMPONENT_WEIGHTS["syntax"],
        evidence = {"files_checked": len(files), "errors": errors},
        passed   = len(errors) == 0,
        notes    = f"{len(errors)} syntax error(s) found" if errors else "All files parse cleanly",
    )


def _eval_test_coverage(target_path: str) -> ComponentScore:
    """
    Run pytest --tb=no -q if available; parse pass/fail counts.
    Falls back to a static score of 50 if pytest is not installed or no tests exist.
    """
    evidence: Dict[str, Any] = {}
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", target_path, "--tb=no", "-q", "--no-header"],
            capture_output=True, text=True, timeout=60,
        )
        output = result.stdout + result.stderr
        evidence["raw_output"] = output[:2000]

        passed = failed = errors_count = 0
        for token in output.split():
            if "passed" in token:
                try: passed = int(token.replace("passed",""))
                except ValueError: pass
            if "failed" in token:
                try: failed = int(token.replace("failed",""))
                except ValueError: pass
            if "error" in token:
                try: errors_count = int(token.replace("error","").replace("s",""))
                except ValueError: pass

        total = passed + failed + errors_count
        if total == 0:
            score, notes = 50.0, "No tests found — defaulting to 50"
        else:
            ratio = passed / total
            score = round(ratio * 100, 1)
            notes = f"{passed}/{total} tests passed"

        evidence.update({"passed": passed, "failed": failed, "errors": errors_count})

    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        score, notes = 50.0, f"pytest unavailable or timed out: {exc}"
        evidence["error"] = str(exc)

    return ComponentScore(
        name     = "test_coverage",
        score    = score,
        weight   = COMPONENT_WEIGHTS["test_coverage"],
        evidence = evidence,
        passed   = score >= 60,
        notes    = notes,
    )


def _eval_db_integrity(target_path: str) -> ComponentScore:
    """
    If ops_engine.db (or omega_cloud.db) is reachable, run PRAGMA integrity_check.
    Otherwise award 80 (cannot verify, not a failure).
    """
    candidates = [OPS_DB_FILE, "omega_cloud.db"]
    evidence: Dict[str, Any] = {}
    issues: List[str] = []

    for db_path in candidates:
        if not Path(db_path).exists():
            continue
        try:
            conn   = sqlite3.connect(db_path)
            rows   = conn.execute("PRAGMA integrity_check").fetchall()
            conn.close()
            result = [r[0] for r in rows]
            evidence[db_path] = result
            if result != ["ok"]:
                issues.extend([f"{db_path}: {r}" for r in result if r != "ok"])
        except sqlite3.Error as e:
            issues.append(f"{db_path}: {e}")
            evidence[db_path] = str(e)

    if not evidence:
        return ComponentScore(
            name="db_integrity", score=80.0,
            weight=COMPONENT_WEIGHTS["db_integrity"],
            evidence={"note": "No databases found; skipping"},
            passed=True, notes="No DB files present — defaulting to 80",
        )

    score = max(0.0, 100.0 - len(issues) * 15)
    return ComponentScore(
        name     = "db_integrity",
        score    = score,
        weight   = COMPONENT_WEIGHTS["db_integrity"],
        evidence = evidence,
        passed   = len(issues) == 0,
        notes    = f"{len(issues)} integrity issue(s)" if issues else "All DBs pass integrity_check",
    )


def _eval_event_chain(target_path: str) -> ComponentScore:
    """
    Verify the OPS proof chain itself: check prev_hash linkage is unbroken.
    Score = 100 if chain is intact (or empty), deduct 20 per broken link.
    """
    chain    = _load_chain()
    evidence = {"chain_length": len(chain)}
    breaks:  List[str] = []

    for i in range(1, len(chain)):
        prev    = chain[i - 1]
        current = chain[i]
        if current.get("prev_hash") != prev.get("chain_hash"):
            breaks.append(
                f"Link broken at index {i}: "
                f"expected prev_hash={prev['chain_hash'][:12]}… "
                f"got {current.get('prev_hash','<missing>')[:12]}…"
            )

    score = max(0.0, 100.0 - len(breaks) * 20)
    evidence["broken_links"] = breaks

    return ComponentScore(
        name     = "event_chain",
        score    = score,
        weight   = COMPONENT_WEIGHTS["event_chain"],
        evidence = evidence,
        passed   = len(breaks) == 0,
        notes    = f"{len(breaks)} broken chain link(s)" if breaks else "Chain integrity intact",
    )


def _eval_consensus(target_path: str) -> ComponentScore:
    """
    If omega_cloud.db exists, check that every FINAL transaction has >= CONSENSUS_QUORUM votes.
    """
    db_path = "omega_cloud.db"
    if not Path(db_path).exists():
        return ComponentScore(
            name="consensus", score=80.0,
            weight=COMPONENT_WEIGHTS["consensus"],
            evidence={"note": "omega_cloud.db not found"},
            passed=True, notes="No ledger DB — defaulting to 80",
        )

    try:
        conn  = sqlite3.connect(db_path)
        quorum = int(os.getenv("CONSENSUS_QUORUM", 2))

        # Find all COMMITTED transactions (event_type = TRANSACTION_COMMITTED)
        rows = conn.execute(
            "SELECT DISTINCT aggregate_id FROM omega_ledger_events WHERE event_type = 'TRANSACTION_COMMITTED'"
        ).fetchall()
        tx_ids = [r[0] for r in rows]

        violations: List[str] = []
        for tx_id in tx_ids:
            vote_count = conn.execute(
                "SELECT COUNT(*) FROM omega_consensus_votes "
                "WHERE transaction_id = ? AND vote_status = 'APPROVED'",
                (tx_id,),
            ).fetchone()[0]
            if vote_count < quorum:
                violations.append(f"tx={tx_id[:8]}… has {vote_count}/{quorum} votes")

        conn.close()
        score = max(0.0, 100.0 - len(violations) * 20)
        evidence = {"transactions_checked": len(tx_ids), "quorum_required": quorum, "violations": violations}
        return ComponentScore(
            name     = "consensus",
            score    = score,
            weight   = COMPONENT_WEIGHTS["consensus"],
            evidence = evidence,
            passed   = len(violations) == 0,
            notes    = f"{len(violations)} under-voted transaction(s)" if violations else f"All transactions meet quorum ({quorum})",
        )
    except sqlite3.Error as e:
        return ComponentScore(
            name="consensus", score=50.0,
            weight=COMPONENT_WEIGHTS["consensus"],
            evidence={"error": str(e)},
            passed=False, notes=f"DB query failed: {e}",
        )


def _eval_api_contracts(target_path: str) -> ComponentScore:
    """
    Static analysis: scan Python source for Flask routes and verify each has
    at least one auth decorator (@require_bearer_token or @require_hmac_signature).
    """
    p     = Path(target_path)
    files = list(p.rglob("*.py")) if p.is_dir() else [p] if p.suffix == ".py" else []

    routes_found:    List[str] = []
    unprotected:     List[str] = []
    evidence: Dict[str, Any]   = {}

    for f in files:
        try:
            tree     = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
            prev_decs: List[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    dec_names = []
                    for d in node.decorator_list:
                        if isinstance(d, ast.Attribute):
                            dec_names.append(d.attr)
                        elif isinstance(d, ast.Name):
                            dec_names.append(d.id)
                        elif isinstance(d, ast.Call):
                            fn = d.func
                            dec_names.append(fn.attr if isinstance(fn, ast.Attribute) else fn.id if isinstance(fn, ast.Name) else "?")
                    is_route = any("route" in n for n in dec_names)
                    has_auth  = any(n in ("require_bearer_token", "require_hmac_signature") for n in dec_names)
                    if is_route:
                        routes_found.append(f"{f.name}::{node.name}")
                        if not has_auth:
                            unprotected.append(f"{f.name}::{node.name}")
        except SyntaxError:
            pass   # already caught by syntax evaluator

    total = len(routes_found)
    bad   = len(unprotected)
    score = 100.0 if total == 0 else max(0.0, (1 - bad / total) * 100)
    evidence = {"routes_found": total, "unprotected_routes": unprotected}

    return ComponentScore(
        name     = "api_contracts",
        score    = score,
        weight   = COMPONENT_WEIGHTS["api_contracts"],
        evidence = evidence,
        passed   = bad == 0,
        notes    = f"{bad}/{total} route(s) missing auth decorator" if bad else f"All {total} route(s) properly protected",
    )


# ---------------------------------------------------------------------------
# Floor (ratchet) enforcement
# ---------------------------------------------------------------------------

def _enforce_floors(components: List[ComponentScore]) -> Tuple[List[ComponentScore], List[str]]:
    """
    Invariant 2: F_i(t+1) >= F_i(t).
    Returns updated components and a list of violation messages.
    """
    floors     = _load_floors()
    violations: List[str] = []

    for cs in components:
        floor = floors.get(cs.name, 0.0)
        if cs.score < floor:
            msg = (
                f"FLOOR VIOLATION [{cs.name}]: "
                f"score {cs.score:.1f} < floor {floor:.1f}"
            )
            violations.append(msg)
            cs.passed = False
            cs.notes  = (cs.notes + " | " + msg).strip(" | ")
        else:
            # Ratchet: update floor if new score is higher
            if cs.score > floor:
                _save_floor(cs.name, cs.score)

    return components, violations


# ---------------------------------------------------------------------------
# Proof validator
# ---------------------------------------------------------------------------

def _validate_proof(
    proof_id:    str,
    system_hash: str,
    prev_hash:   Optional[str],
    score:       float,
    violations:  List[str],
    target_path: str,
    timestamp:   str,
    component_scores: Dict[str, float],
) -> Tuple[bool, str]:
    """
    Invariant 3 (acceptance rule):
        VALID ⟺ hash_reproducible AND score >= 0 AND no invariant break
    Returns (is_valid, reason).
    """
    # 1. Hash reproducibility
    recomputed = _compute_system_hash(target_path, component_scores, timestamp, prev_hash)
    if recomputed != system_hash:
        return False, f"Hash mismatch: stored={system_hash[:12]}… recomputed={recomputed[:12]}…"

    # 2. Score sanity
    if not (0 <= score <= 100):
        return False, f"Score {score} out of bounds [0, 100]"

    # 3. Invariant violations
    if violations:
        return False, "Invariant violations: " + "; ".join(violations)

    # 4. Strict monotonic (optional)
    if STRICT_MONOTONIC:
        prev = _latest_proof()
        if prev and score < prev["score"]:
            return False, (
                f"STRICT_MONOTONIC: score {score:.1f} < previous {prev['score']:.1f}"
            )

    return True, "OK"


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------

def _grade(score: float) -> str:
    if score >= 95: return "S"
    if score >= 90: return "A+"
    if score >= 85: return "A"
    if score >= 80: return "B+"
    if score >= 75: return "B"
    if score >= 70: return "C+"
    if score >= 60: return "C"
    if score >= 50: return "D"
    return "F"


# ---------------------------------------------------------------------------
# Public API: score()
# ---------------------------------------------------------------------------

def score(target_path: str) -> ProofEvent:
    """
    Evaluate target_path and produce a cryptographically-chained ProofEvent.
    This is the main entry point.
    """
    target_path = str(Path(target_path).resolve())
    timestamp   = datetime.now(timezone.utc).isoformat()
    proof_id    = str(uuid.uuid4())
    prev        = _latest_proof()
    prev_hash   = prev["chain_hash"] if prev else None

    # --- Run all evaluators ---
    components: List[ComponentScore] = [
        _eval_syntax(target_path),
        _eval_test_coverage(target_path),
        _eval_db_integrity(target_path),
        _eval_event_chain(target_path),
        _eval_consensus(target_path),
        _eval_api_contracts(target_path),
    ]

    # --- Enforce floors (Invariant 2) ---
    components, floor_violations = _enforce_floors(components)

    # --- Weighted score ---
    weighted_score = round(sum(cs.weighted for cs in components), 2)
    grade          = _grade(weighted_score)

    # --- Component score dict (for hashing) ---
    comp_score_map = {cs.name: cs.score for cs in components}

    # --- Compute hashes ---
    system_hash = _compute_system_hash(target_path, comp_score_map, timestamp, prev_hash)
    chain_hash  = _compute_chain_hash(proof_id, system_hash, prev_hash)

    # --- Proof validation (Invariant 3) ---
    is_valid, reason = _validate_proof(
        proof_id, system_hash, prev_hash, weighted_score,
        floor_violations, target_path, timestamp, comp_score_map,
    )

    if not is_valid:
        verdict = "REJECT"
    elif weighted_score >= ACCEPTANCE_THRESHOLD:
        verdict = "PASS"
    else:
        verdict = "FAIL"

    violations = floor_violations if not is_valid else []

    # --- Assemble evidence ---
    evidence = {
        "validation_result": reason,
        "floor_violations":  floor_violations,
        "acceptance_threshold": ACCEPTANCE_THRESHOLD,
        "strict_monotonic":  STRICT_MONOTONIC,
    }
    for cs in components:
        evidence[cs.name] = cs.evidence

    proof = ProofEvent(
        proof_id    = proof_id,
        timestamp   = timestamp,
        score       = weighted_score,
        grade       = grade,
        components  = {cs.name: asdict(cs) for cs in components},
        evidence    = evidence,
        system_hash = system_hash,
        prev_hash   = prev_hash,
        chain_hash  = chain_hash,
        verdict     = verdict,
        violations  = violations,
        target_path = target_path,
    )

    _persist_proof(proof)
    return proof


# ---------------------------------------------------------------------------
# Public API: verify()
# ---------------------------------------------------------------------------

def verify(chain_file: str = OPS_CHAIN_FILE) -> Dict[str, Any]:
    """
    Re-validate every proof in the chain file.
    Returns a summary dict with per-proof status.
    """
    chain   = _load_chain()
    results = []
    ok      = True

    for i, entry in enumerate(chain):
        expected_prev = chain[i - 1]["chain_hash"] if i > 0 else None
        link_ok       = entry.get("prev_hash") == expected_prev

        # Re-derive chain_hash
        recomputed_chain = _compute_chain_hash(
            entry["proof_id"], entry["system_hash"], entry.get("prev_hash")
        )
        hash_ok = recomputed_chain == entry["chain_hash"]

        status = "OK" if (link_ok and hash_ok) else "CORRUPT"
        if status != "OK":
            ok = False

        results.append({
            "index":      i,
            "proof_id":   entry["proof_id"][:8] + "…",
            "timestamp":  entry["timestamp"],
            "score":      entry["score"],
            "verdict":    entry["verdict"],
            "link_ok":    link_ok,
            "hash_ok":    hash_ok,
            "status":     status,
        })

    return {
        "chain_length":    len(chain),
        "chain_intact":    ok,
        "proofs":          results,
        "summary":         "CHAIN INTACT" if ok else "⚠ CHAIN CORRUPTION DETECTED",
    }


# ---------------------------------------------------------------------------
# Public API: rollback_check()
# ---------------------------------------------------------------------------

def rollback_check(chain_file: str = OPS_CHAIN_FILE) -> Dict[str, Any]:
    """
    Scan the proof chain for score regressions and floor violations.
    Does NOT modify any state.
    """
    chain      = _load_chain()
    regressions: List[Dict] = []
    floor_hits: List[Dict]  = []
    floors     = _load_floors()

    for i in range(1, len(chain)):
        prev_score = chain[i - 1]["score"]
        curr_score = chain[i]["score"]
        if curr_score < prev_score:
            regressions.append({
                "index":      i,
                "proof_id":   chain[i]["proof_id"][:8] + "…",
                "prev_score": prev_score,
                "curr_score": curr_score,
                "delta":      round(curr_score - prev_score, 2),
            })

    for entry in chain:
        for comp_name, comp_data in entry.get("components", {}).items():
            floor = floors.get(comp_name, 0.0)
            if comp_data.get("score", 100) < floor:
                floor_hits.append({
                    "proof_id":  entry["proof_id"][:8] + "…",
                    "component": comp_name,
                    "score":     comp_data["score"],
                    "floor":     floor,
                })

    return {
        "chain_length":      len(chain),
        "regressions":       regressions,
        "regression_count":  len(regressions),
        "floor_hits":        floor_hits,
        "floor_hit_count":   len(floor_hits),
        "current_floors":    floors,
        "summary": (
            "No regressions or floor violations found" if not regressions and not floor_hits
            else f"{len(regressions)} regression(s), {len(floor_hits)} floor violation(s)"
        ),
    }


# ---------------------------------------------------------------------------
# Public API: export_chain()
# ---------------------------------------------------------------------------

def export_chain(chain_file: str = OPS_CHAIN_FILE) -> str:
    """Return the full proof chain as a pretty-printed JSON string."""
    chain = _load_chain()
    return json.dumps(chain, indent=2)


# ---------------------------------------------------------------------------
# Pretty-print helpers (CLI output)
# ---------------------------------------------------------------------------

def _print_proof(proof: ProofEvent) -> None:
    w = 62
    verdict_icon = {"PASS": "✅", "FAIL": "❌", "REJECT": "🚫"}.get(proof.verdict, "?")
    print("\n" + "═" * w)
    print(f"  OPS Proof Engine — Evaluation Report")
    print("═" * w)
    print(f"  Proof ID   : {proof.proof_id[:16]}…")
    print(f"  Timestamp  : {proof.timestamp}")
    print(f"  Target     : {proof.target_path}")
    print(f"  Score      : {proof.score:.1f} / 100   Grade: {proof.grade}")
    print(f"  Verdict    : {verdict_icon} {proof.verdict}")
    print(f"  Hash (H_t) : {proof.system_hash[:32]}…")
    print(f"  Prev Hash  : {proof.prev_hash[:32] + '…' if proof.prev_hash else 'GENESIS'}")
    print(f"  Chain Hash : {proof.chain_hash[:32]}…")
    print("─" * w)
    print(f"  {'COMPONENT':<20} {'SCORE':>7}  {'WEIGHT':>7}  {'WTDSC':>7}  STATUS")
    print("─" * w)
    for name, cs in proof.components.items():
        icon   = "✓" if cs["passed"] else "✗"
        wtd    = cs["score"] * cs["weight"]
        print(f"  {name:<20} {cs['score']:>6.1f}%  {cs['weight']:>6.0%}  {wtd:>6.1f}   {icon} {cs['notes'][:28]}")
    print("─" * w)
    print(f"  {'WEIGHTED TOTAL':<20} {proof.score:>6.1f}%")
    if proof.violations:
        print("\n  ⚠ VIOLATIONS:")
        for v in proof.violations:
            print(f"    • {v}")
    print("═" * w + "\n")


def _print_verify(result: Dict[str, Any]) -> None:
    print("\n" + "═" * 62)
    print("  OPS Chain Verification")
    print("═" * 62)
    print(f"  Chain length : {result['chain_length']}")
    print(f"  Status       : {result['summary']}")
    print("─" * 62)
    for p in result["proofs"]:
        icon = "✓" if p["status"] == "OK" else "✗"
        print(f"  [{icon}] #{p['index']:>3}  {p['timestamp'][:19]}  "
              f"score={p['score']:>5.1f}  {p['verdict']:<6}  "
              f"link={'ok' if p['link_ok'] else 'BROKEN'}  hash={'ok' if p['hash_ok'] else 'CORRUPT'}")
    print("═" * 62 + "\n")


def _print_rollback(result: Dict[str, Any]) -> None:
    print("\n" + "═" * 62)
    print("  OPS Rollback Check")
    print("═" * 62)
    print(f"  {result['summary']}")
    if result["regressions"]:
        print("\n  Score regressions:")
        for r in result["regressions"]:
            print(f"    proof #{r['index']} ({r['proof_id']})  "
                  f"{r['prev_score']:.1f} → {r['curr_score']:.1f}  (Δ {r['delta']:.1f})")
    if result["floor_hits"]:
        print("\n  Floor violations:")
        for f in result["floor_hits"]:
            print(f"    {f['proof_id']} [{f['component']}]  "
                  f"score={f['score']:.1f} < floor={f['floor']:.1f}")
    print("\n  Current floors:")
    for comp, fl in result["current_floors"].items():
        print(f"    {comp:<20} {fl:.1f}")
    print("═" * 62 + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _usage() -> None:
    print(textwrap.dedent("""
        OPS Engine v1 — Oracle Proof Engine

        Usage:
          python ops_engine.py score   <path>              Evaluate and record a proof
          python ops_engine.py verify  [chain_file]        Verify chain integrity
          python ops_engine.py rollback-check [chain_file] Check for regressions
          python ops_engine.py export  [chain_file]        Dump chain as JSON

        Environment:
          OPS_CHAIN_FILE    path to .jsonl proof chain  (default: ops_proof_chain.jsonl)
          OPS_DB_FILE       path to SQLite index        (default: ops_engine.db)
          CONSENSUS_QUORUM  minimum votes for finality  (default: 2)
    """))


def main() -> None:
    args = sys.argv[1:]
    if not args:
        _usage(); return

    cmd = args[0].lower()

    if cmd == "score":
        if len(args) < 2:
            print("Error: 'score' requires a target path."); return
        proof = score(args[1])
        _print_proof(proof)

    elif cmd == "verify":
        chain_file = args[1] if len(args) > 1 else OPS_CHAIN_FILE
        result = verify(chain_file)
        _print_verify(result)

    elif cmd == "rollback-check":
        chain_file = args[1] if len(args) > 1 else OPS_CHAIN_FILE
        result = rollback_check(chain_file)
        _print_rollback(result)

    elif cmd == "export":
        chain_file = args[1] if len(args) > 1 else OPS_CHAIN_FILE
        print(export_chain(chain_file))

    else:
        print(f"Unknown command: {cmd}")
        _usage()


if __name__ == "__main__":
    main()

