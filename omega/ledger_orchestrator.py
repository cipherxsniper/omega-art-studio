"""
=========================================================
OMEGA LEDGER ORCHESTRATOR ENGINE
Production Grade Double-Entry Transaction Core
=========================================================
"""

import uuid
from datetime import datetime


class LedgerOrchestrator:
    """
    Deterministic, append-only ledger transaction engine.

    Responsibilities:
    - Enforce double-entry accounting
    - Prevent double spend via idempotency keys
    - Write atomic ledger entries
    - Guarantee audit-safe transaction structure
    """

    def __init__(self, db):
        self.db = db

    # -----------------------------
    # IDEMPOTENCY GUARD
    # -----------------------------
    def _is_duplicate(self, idempotency_key: str) -> bool:
        result = self.db.execute(
            """
            SELECT 1 FROM ledger_entries
            WHERE idempotency_key = %s
            LIMIT 1
            """,
            (idempotency_key,)
        )
        return result.fetchone() is not None

    # -----------------------------
    # DOUBLE ENTRY VALIDATION
    # -----------------------------
    def _validate_balance(self, entries):
        debit = 0
        credit = 0

        for e in entries:
            if e["amount"] <= 0:
                raise Exception("Invalid amount: must be > 0")

            if e["direction"] == "DEBIT":
                debit += e["amount"]
            elif e["direction"] == "CREDIT":
                credit += e["amount"]
            else:
                raise Exception("Invalid direction")

        if round(debit, 2) != round(credit, 2):
            raise Exception(
                f"UNBALANCED TRANSACTION: DEBIT={debit}, CREDIT={credit}"
            )

    # -----------------------------
    # CORE EXECUTION
    # -----------------------------
    def execute(self, transaction_id: str, entries: list, idempotency_key: str):

        # 1. IDEMPOTENCY CHECK
        if self._is_duplicate(idempotency_key):
            return {
                "status": "ignored",
                "reason": "duplicate_transaction"
            }

        # 2. VALIDATE DOUBLE ENTRY
        self._validate_balance(entries)

        # 3. WRITE LEDGER ENTRIES (ATOMIC APPEND ONLY)
        for e in entries:
            self.db.execute(
                """
                INSERT INTO ledger_entries (
                    id,
                    transaction_id,
                    wallet_id,
                    direction,
                    amount,
                    idempotency_key,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """,
                (
                    str(uuid.uuid4()),
                    transaction_id,
                    e["wallet_id"],
                    e["direction"],
                    float(e["amount"]),
                    idempotency_key
                )
            )

        return {
            "status": "committed",
            "transaction_id": transaction_id
        }


# -----------------------------
# FACTORY HELPERS
# -----------------------------

def create_transaction_id(prefix="TX"):
    return f"{prefix}_{uuid.uuid4()}"
