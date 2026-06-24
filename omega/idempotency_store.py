"""
Simple idempotency tracking layer (safe + minimal)
"""

def record_idempotency(db, key: str):
    db.execute(
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
        VALUES (
            gen_random_uuid(),
            gen_random_uuid(),
            NULL,
            'CREDIT',
            0,
            %s,
            NOW()
        )
        ON CONFLICT (idempotency_key) DO NOTHING
        """,
        (key,)
    )
