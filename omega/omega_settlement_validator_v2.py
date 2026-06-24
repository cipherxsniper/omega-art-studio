from omega_db_kernel_v1 import OmegaTransaction

FORBIDDEN_NEGATIVE = {
    "TREASURY",
    "FOUNDER",
    "CREDIT",
    "INVESTMENT"
}

def validate(cur):
    cur.execute("""
        SELECT
            account_type,
            SUM(
                CASE
                    WHEN direction = 'CREDIT' THEN amount
                    ELSE -amount
                END
            ) AS balance
        FROM ledger_postings
        GROUP BY account_type
    """)
    rows = cur.fetchall()

    violations = []

    for r in rows:
        if r["account_type"] in FORBIDDEN_NEGATIVE and r["balance"] < 0:
            violations.append(r)

    if violations:
        print("❌ SETTLEMENT INVALID")
        print(violations)
        return {"status": "FAILED"}

    print("✅ SETTLEMENT VALIDATED V2")
    return {"status": "OK"}


if __name__ == "__main__":
    with OmegaTransaction() as cur:
        validate(cur)
