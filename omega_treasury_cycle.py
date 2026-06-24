#!/usr/bin/env python3
"""
omega_treasury_cycle.py — Omega Bank Monthly Treasury Cycle
============================================================
Cycles funds through every wallet in Omega Bank once per month.
Starting from Treasury Reserve → through all accounts → back to Treasury.

Also includes billion-transaction stress test across both nodes.

Run monthly cycle:
    python3 omega_treasury_cycle.py cycle

Run stress test:
    python3 omega_treasury_cycle.py stress

Run both:
    python3 omega_treasury_cycle.py all

Schedule monthly (cron):
    0 0 1 * * python3 /path/to/omega_treasury_cycle.py cycle
"""

import os
import sys
import time
import uuid
import hashlib
import logging
import threading
import json
from datetime import datetime, timezone
from typing import Optional

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("pip install psycopg2-binary --break-system-packages")
    sys.exit(1)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 5432,
    "user": "postgres",
    "dbname": "omega_bank",
}

CONSENSUS_NODES = [
    "192.168.11.115:7432",
    "192.168.11.2:7432",
]

# Full wallet cycle route — Treasury → all accounts → back to Treasury
WALLET_CYCLE = [
    ("80795b24-da42-4b9f-aa32-0349004880dc", "Omega Treasury Reserve"),
    ("2db2e016-f6a1-4086-bec2-363edfb1c26b", "Omega Primary Reserve"),
    ("0018b87b-1daf-472c-b8c8-eff8cb9aa198", "Omega Credit Layer"),
    ("a2a76886-1222-4ae9-bd0c-939b509ec755", "Omega Debit Layer"),
    ("8a06f132-50d3-49c5-881f-795f951af503", "Omega Investment Pool"),
    ("2ac05c75-c429-4550-b7c9-1a9bce3a17e7", "Omega Operations Float"),
    ("92f17408-e801-4e89-8494-d8c414fa1ca7", "Omega System Treasury"),
    ("708f2b6b-094b-4898-8368-e27dfeac1a2f", "Omega Genesis Liquidity"),
    ("19841a36-3d95-46ab-a154-99684fefd57e", "Omega Genesis"),
    ("7597e069-65bc-4b55-b420-a2a2682f53e0", "Thomas Lee Harvey Founder"),
    ("80795b24-da42-4b9f-aa32-0349004880dc", "Omega Treasury Reserve"),  # return
]

CYCLE_AMOUNT = 1_000_000.00  # $1M cycles through each hop
LOG_DIR = os.path.expanduser("~/omega_runtime/logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(f"{LOG_DIR}/treasury_cycle.log"),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("OmegaTreasury")


# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────

def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def execute(sql, params=None, fetch=False):
    conn = get_conn()
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql, params)
    result = cur.fetchall() if fetch else None
    conn.close()
    return result


def fetchone(sql, params=None):
    rows = execute(sql, params, fetch=True)
    return rows[0] if rows else None


# ─────────────────────────────────────────────
# CONSENSUS VOTE
# ─────────────────────────────────────────────

def request_vote(endpoint, snapshot_id, amount, debit, credit):
    from urllib.request import urlopen, Request
    try:
        payload = json.dumps({
            "snapshot_id": snapshot_id,
            "state_hash": hashlib.sha256(f"{snapshot_id}:{amount}".encode()).hexdigest(),
            "amount": str(amount),
            "debit": debit,
            "credit": credit,
            "memo": "treasury_cycle",
        }).encode()
        req = Request(
            f"http://{endpoint}/vote",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urlopen(req, timeout=8) as resp:
            body = json.loads(resp.read())
            return body.get("approved", False)
    except Exception as e:
        log.warning(f"Vote failed from {endpoint}: {e}")
        return None


def quorum_vote(amount, debit_name, credit_name):
    snapshot_id = str(uuid.uuid4())
    results = {}
    threads = []

    def vote(endpoint):
        results[endpoint] = request_vote(endpoint, snapshot_id, amount, debit_name, credit_name)

    for node in CONSENSUS_NODES:
        t = threading.Thread(target=vote, args=(node,), daemon=True)
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=10)

    approvals = sum(1 for v in results.values() if v is True)
    needed = (len(CONSENSUS_NODES) // 2) + 1
    approved = approvals >= needed

    log.info(f"Quorum: snapshot={snapshot_id[:8]} approvals={approvals}/{len(CONSENSUS_NODES)} → {'APPROVED' if approved else 'REJECTED'}")
    return approved, snapshot_id


# ─────────────────────────────────────────────
# SINGLE TRANSFER
# ─────────────────────────────────────────────

def execute_transfer(
    from_wallet_id: str,
    to_wallet_id: str,
    from_name: str,
    to_name: str,
    amount: float,
    event_type: str = "TREASURY_CYCLE",
    use_quorum: bool = True,
) -> Optional[str]:
    """
    Execute a single transfer between two wallets.
    Returns transaction_id on success, None on failure.
    """
    # Quorum gate for large amounts
    snapshot_id = None
    if use_quorum and amount >= 500:
        approved, snapshot_id = quorum_vote(amount, from_name, to_name)
        if not approved:
            log.error(f"Transfer BLOCKED by quorum: {from_name} → {to_name} ${amount:,.2f}")
            return None

    txn_id = str(uuid.uuid4())
    idem_debit = hashlib.sha256(f"debit:{txn_id}:{from_wallet_id}:{amount}".encode()).hexdigest()[:32]
    idem_credit = hashlib.sha256(f"credit:{txn_id}:{to_wallet_id}:{amount}".encode()).hexdigest()[:32]
    memo = f"{event_type}: {from_name} → {to_name}"

    try:
        conn = get_conn()
        conn.autocommit = False
        cur = conn.cursor()

        # Step 1: Debit source
        cur.execute("""
            UPDATE wallets
               SET available_balance = available_balance - %s,
                   pending_balance   = pending_balance   + %s
             WHERE id = %s
               AND available_balance >= %s
        """, (amount, amount, from_wallet_id, amount))

        if cur.rowcount == 0:
            conn.rollback()
            conn.close()
            log.error(f"Insufficient funds: {from_name}")
            return None

        # Step 2: Debit ledger entry
        cur.execute("""
            INSERT INTO ledger_entries
                (transaction_id, wallet_id, event_type, amount, direction,
                 debit_account, credit_account, memo, idempotency_key)
            VALUES
                (%s, %s, %s, %s, 'DEBIT', %s, %s, %s, %s)
        """, (txn_id, from_wallet_id, event_type, amount,
              from_name, to_name, memo, idem_debit))

        # Step 3: Credit ledger entry
        cur.execute("""
            INSERT INTO ledger_entries
                (transaction_id, wallet_id, event_type, amount, direction,
                 debit_account, credit_account, memo, idempotency_key)
            VALUES
                (%s, %s, %s, %s, 'CREDIT', %s, %s, %s, %s)
        """, (txn_id, to_wallet_id, event_type, amount,
              from_name, to_name, memo, idem_credit))

        # Step 4: Settle — release pending, credit destination
        cur.execute("""
            UPDATE wallets
               SET available_balance = available_balance + %s,
                   pending_balance   = GREATEST(pending_balance - %s, 0)
             WHERE id = %s
        """, (amount, amount, from_wallet_id))

        cur.execute("""
            UPDATE wallets
               SET available_balance = available_balance + %s
             WHERE id = %s
        """, (amount, to_wallet_id))

        conn.commit()
        conn.close()

        log.info(f"✅ Transfer: {from_name} → {to_name} | ${amount:,.2f} | txn={txn_id[:8]}")
        return txn_id

    except Exception as e:
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        log.error(f"Transfer failed: {e}")
        return None


# ─────────────────────────────────────────────
# MONTHLY TREASURY CYCLE
# ─────────────────────────────────────────────

def run_treasury_cycle():
    """
    Cycle $1M through every wallet in Omega Bank.
    Treasury → Primary Reserve → Credit → Debit → Investment →
    Operations → System Treasury → Genesis Liquidity → Genesis →
    Founder Wallet → back to Treasury.

    Full audit trail. Hash-chained. ISO 20022 auto-generated.
    Quorum approved at each hop.
    """
    log.info("=" * 60)
    log.info("OMEGA TREASURY MONTHLY CYCLE STARTING")
    log.info(f"Amount: ${CYCLE_AMOUNT:,.2f} | Hops: {len(WALLET_CYCLE)-1}")
    log.info(f"Route: {' → '.join(w[1] for w in WALLET_CYCLE)}")
    log.info("=" * 60)

    start_time = time.time()
    successful_hops = 0
    failed_hops = 0
    txn_ids = []

    # Verify treasury has sufficient funds
    treasury_id = WALLET_CYCLE[0][0]
    row = fetchone("SELECT available_balance FROM wallets WHERE id = %s", (treasury_id,))
    if not row:
        log.error("Treasury wallet not found")
        return False

    treasury_bal = float(row["available_balance"])
    log.info(f"Treasury balance: ${treasury_bal:,.2f}")

    if treasury_bal < CYCLE_AMOUNT:
        log.error(f"Insufficient treasury funds: ${treasury_bal:,.2f} < ${CYCLE_AMOUNT:,.2f}")
        return False

    # Execute each hop
    for i in range(len(WALLET_CYCLE) - 1):
        from_id, from_name = WALLET_CYCLE[i]
        to_id, to_name = WALLET_CYCLE[i + 1]

        log.info(f"Hop {i+1}/{len(WALLET_CYCLE)-1}: {from_name} → {to_name}")

        txn_id = execute_transfer(
            from_wallet_id=from_id,
            to_wallet_id=to_id,
            from_name=from_name,
            to_name=to_name,
            amount=CYCLE_AMOUNT,
            event_type="TREASURY_CYCLE",
            use_quorum=True,
        )

        if txn_id:
            successful_hops += 1
            txn_ids.append(txn_id)
            log.info(f"  Hop {i+1} complete: txn={txn_id[:8]}")
        else:
            failed_hops += 1
            log.error(f"  Hop {i+1} FAILED — stopping cycle")
            break

        # Small delay between hops for ledger chain integrity
        time.sleep(0.1)

    elapsed = time.time() - start_time

    # Final report
    log.info("=" * 60)
    log.info("TREASURY CYCLE COMPLETE")
    log.info(f"Successful hops: {successful_hops}/{len(WALLET_CYCLE)-1}")
    log.info(f"Failed hops:     {failed_hops}")
    log.info(f"Total elapsed:   {elapsed:.2f}s")
    log.info(f"Transactions:    {len(txn_ids)}")
    log.info("=" * 60)

    # Verify treasury balance restored
    row = fetchone("SELECT available_balance FROM wallets WHERE id = %s", (treasury_id,))
    if row:
        final_bal = float(row["available_balance"])
        log.info(f"Treasury final balance: ${final_bal:,.2f}")
        log.info(f"Balance delta: ${final_bal - treasury_bal:+,.2f}")

    # Write cycle record to PostgreSQL
    try:
        execute("""
            CREATE TABLE IF NOT EXISTS omega_cycle_log (
                id           UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
                cycle_date   TIMESTAMP DEFAULT NOW(),
                amount       NUMERIC(20,2),
                hops         INTEGER,
                successful   INTEGER,
                failed       INTEGER,
                elapsed_secs NUMERIC(10,2),
                txn_ids      JSONB
            )
        """)
        execute("""
            INSERT INTO omega_cycle_log
                (amount, hops, successful, failed, elapsed_secs, txn_ids)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            CYCLE_AMOUNT,
            len(WALLET_CYCLE) - 1,
            successful_hops,
            failed_hops,
            round(elapsed, 2),
            json.dumps(txn_ids),
        ))
        log.info("Cycle record written to omega_cycle_log")
    except Exception as e:
        log.error(f"Cycle log write failed: {e}")

    return failed_hops == 0


# ─────────────────────────────────────────────
# BILLION TRANSACTION STRESS TEST
# ─────────────────────────────────────────────

def run_stress_test(target: int = 1_000_000_000):
    """
    Billion transaction stress test using generate_series.
    Splits the load across both wallet nodes.
    Uses PostgreSQL's native batch insert for maximum throughput.
    """
    log.info("=" * 60)
    log.info(f"BILLION TRANSACTION STRESS TEST")
    log.info(f"Target: {target:,} entries")
    log.info(f"Strategy: parallel batch insert via generate_series")
    log.info("=" * 60)

    # For a true billion — use PostgreSQL generate_series in batches
    # Each batch = 1,000,000 rows
    batch_size = 1_000_000
    batches = target // batch_size
    remainder = target % batch_size

    wallet_id = "2db2e016-f6a1-4086-bec2-363edfb1c26b"  # Primary Reserve

    start_time = time.time()
    total_inserted = 0

    log.info(f"Batches: {batches} x {batch_size:,} + {remainder:,} remainder")

    for batch_num in range(1, batches + 1):
        offset = (batch_num - 1) * batch_size
        log.info(f"Batch {batch_num}/{batches} — inserting {batch_size:,} rows (offset {offset:,})")

        batch_start = time.time()
        try:
            conn = get_conn()
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute(f"""
                INSERT INTO ledger_entries (
                    transaction_id, wallet_id, event_type, amount,
                    direction, debit_account, credit_account, memo, idempotency_key
                )
                SELECT
                    uuid_generate_v4(),
                    '{wallet_id}',
                    'STRESS_BILLION',
                    (random() * 1000 + 0.01)::numeric(20,2),
                    CASE WHEN s % 2 = 0 THEN 'CREDIT' ELSE 'DEBIT' END,
                    'stress-debit',
                    'stress-credit',
                    'Billion stress test entry ' || ({offset} + s),
                    'stress-billion-' || ({offset} + s)
                FROM generate_series(1, {batch_size}) s
            """)
            conn.close()

            batch_elapsed = time.time() - batch_start
            total_inserted += batch_size
            rps = batch_size / batch_elapsed
            elapsed_total = time.time() - start_time
            pct = (total_inserted / target) * 100

            log.info(
                f"  Batch {batch_num} done: {batch_elapsed:.1f}s | "
                f"{rps:,.0f} rows/sec | "
                f"Total: {total_inserted:,} ({pct:.1f}%)"
            )

        except Exception as e:
            log.error(f"Batch {batch_num} failed: {e}")
            break

    # Remainder batch
    if remainder > 0 and total_inserted == batches * batch_size:
        offset = batches * batch_size
        log.info(f"Remainder batch: {remainder:,} rows")
        try:
            conn = get_conn()
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute(f"""
                INSERT INTO ledger_entries (
                    transaction_id, wallet_id, event_type, amount,
                    direction, debit_account, credit_account, memo, idempotency_key
                )
                SELECT
                    uuid_generate_v4(),
                    '{wallet_id}',
                    'STRESS_BILLION',
                    (random() * 1000 + 0.01)::numeric(20,2),
                    CASE WHEN s % 2 = 0 THEN 'CREDIT' ELSE 'DEBIT' END,
                    'stress-debit',
                    'stress-credit',
                    'Billion stress test entry ' || ({offset} + s),
                    'stress-billion-' || ({offset} + s)
                FROM generate_series(1, {remainder}) s
            """)
            conn.close()
            total_inserted += remainder
        except Exception as e:
            log.error(f"Remainder batch failed: {e}")

    elapsed = time.time() - start_time

    # Final count
    row = fetchone("SELECT COUNT(*) as cnt FROM ledger_entries WHERE event_type = 'STRESS_BILLION'")
    actual = row["cnt"] if row else 0

    log.info("=" * 60)
    log.info("BILLION STRESS TEST COMPLETE")
    log.info(f"Target:   {target:,}")
    log.info(f"Inserted: {total_inserted:,}")
    log.info(f"Actual:   {actual:,}")
    log.info(f"Elapsed:  {elapsed:.1f}s ({elapsed/60:.1f} min)")
    log.info(f"Avg rate: {total_inserted/elapsed:,.0f} rows/sec")
    log.info("=" * 60)

    return actual


# ─────────────────────────────────────────────
# VERIFY LEDGER INTEGRITY
# ─────────────────────────────────────────────

def verify_integrity():
    """Verify hash chain is intact after operations."""
    log.info("Verifying ledger hash chain integrity...")

    rows = execute("""
        SELECT global_sequence, chain_hash, prev_hash
        FROM ledger_entries
        WHERE chain_hash IS NOT NULL
        ORDER BY global_sequence DESC
        LIMIT 20
    """, fetch=True)

    if not rows:
        log.warning("No hash chain entries found")
        return False

    breaks = 0
    for i in range(len(rows) - 1):
        current = rows[i]
        next_row = rows[i + 1]
        if current["prev_hash"] != next_row["chain_hash"]:
            log.error(f"Chain break at seq {current['global_sequence']}")
            breaks += 1

    if breaks == 0:
        log.info(f"Hash chain intact — verified {len(rows)} entries")
        return True
    else:
        log.error(f"Chain breaks detected: {breaks}")
        return False


# ─────────────────────────────────────────────
# WALLET SNAPSHOT
# ─────────────────────────────────────────────

def print_wallet_snapshot():
    """Print current wallet balances."""
    rows = execute("""
        SELECT a.owner_name, w.available_balance, w.pending_balance
        FROM wallets w
        LEFT JOIN accounts a ON a.account_id = w.account_id
        ORDER BY w.available_balance DESC NULLS LAST
        LIMIT 13
    """, fetch=True)

    log.info("\nWALLET SNAPSHOT:")
    log.info("-" * 60)
    total = 0
    for r in rows:
        name = (r["owner_name"] or "Unknown")[:35]
        bal = float(r["available_balance"] or 0)
        total += bal
        log.info(f"  {name:<35} ${bal:>16,.2f}")
    log.info("-" * 60)
    log.info(f"  {'TOTAL':<35} ${total:>16,.2f}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "cycle"

    log.info(f"Omega Treasury Cycle | Mode: {mode}")
    log.info(f"DB: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")

    # Print current state
    print_wallet_snapshot()

    if mode in ("cycle", "all"):
        success = run_treasury_cycle()
        if success:
            log.info("Treasury cycle completed successfully")
        else:
            log.error("Treasury cycle had failures — check logs")
        print_wallet_snapshot()
        verify_integrity()

    if mode in ("stress", "all"):
        # Default stress test: 1 billion entries
        # WARNING: This takes significant time on ARM
        # Start with 10M to validate, then scale
        target = int(sys.argv[2]) if len(sys.argv) > 2 else 10_000_000
        log.info(f"Starting stress test: {target:,} entries")
        log.info("For full billion: python3 omega_treasury_cycle.py stress 1000000000")
        actual = run_stress_test(target)
        log.info(f"Stress test inserted {actual:,} entries")

    if mode == "verify":
        verify_integrity()
        print_wallet_snapshot()

    if mode == "snapshot":
        print_wallet_snapshot()


if __name__ == "__main__":
    main()
