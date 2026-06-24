#!/usr/bin/env python3
import psycopg2
from decimal import Decimal
from collections import defaultdict
from datetime import datetime, timedelta

"""
OMEGA REAL-TIME FRAUD SIGNATURE ENGINE
Behavioral velocity + anomaly scoring (deterministic)
"""

# ----------------------------
# CONFIG THRESHOLDS (TUNABLE)
# ----------------------------
MAX_TX_PER_MIN = 10
MAX_VOLUME_PER_MIN = Decimal("5000")
RISK_SCORE_ALERT = 70


# ----------------------------
# FETCH RECENT ACTIVITY WINDOW
# ----------------------------
def fetch_recent(cur, wallet_id):
    cur.execute("""
        SELECT amount, direction, created_at
        FROM ledger_entries
        WHERE wallet_id = %s
          AND created_at > now() - interval '10 minutes'
    """, (wallet_id,))
    return cur.fetchall()


# ----------------------------
# BUILD FRAUD SIGNATURE
# ----------------------------
def compute_signature(transactions):
    count = len(transactions)
    volume = Decimal("0")

    for amount, direction, _ in transactions:
        amt = Decimal(str(amount))
        volume += amt if direction == "CREDIT" else amt

    return {
        "tx_count": count,
        "volume": volume
    }


# ----------------------------
# RISK SCORING ENGINE
# ----------------------------
def score_risk(signature):
    score = 0

    if signature["tx_count"] > MAX_TX_PER_MIN:
        score += 40

    if signature["volume"] > MAX_VOLUME_PER_MIN:
        score += 50

    return min(score, 100)


# ----------------------------
# EMIT FRAUD EVENT
# ----------------------------
def emit_alert(cur, wallet_id, score, signature):
    cur.execute("""
        INSERT INTO invariant_failures (
            wallet_id,
            failure_type,
            severity,
            message,
            created_at
        )
        VALUES (%s, %s, %s, %s, now())
    """, (
        wallet_id,
        "FRAUD_SIGNATURE",
        "HIGH" if score > 70 else "MEDIUM",
        f"tx={signature['tx_count']} volume={signature['volume']} score={score}"
    ))


# ----------------------------
# MAIN DETECTION LOOP
# ----------------------------
def evaluate_wallet(cur, wallet_id):
    tx = fetch_recent(cur, wallet_id)

    signature = compute_signature(tx)
    score = score_risk(signature)

    if score >= RISK_SCORE_ALERT:
        emit_alert(cur, wallet_id, score, signature)

    return {
        "wallet_id": wallet_id,
        "tx_count": signature["tx_count"],
        "volume": str(signature["volume"]),
        "risk_score": score
    }


# ----------------------------
# ENTRYPOINT
# ----------------------------
def run():
    conn = psycopg2.connect(dbname="omega_bank", user="omega")

    with conn.cursor() as cur:
        cur.execute("SELECT id FROM wallets")

        results = []

        for (wallet_id,) in cur.fetchall():
            results.append(evaluate_wallet(cur, wallet_id))

        conn.commit()

    for r in results:
        print(r)


if __name__ == "__main__":
    run()
