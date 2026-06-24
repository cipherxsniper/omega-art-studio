from omega_db_kernel_v1 import OmegaTransaction

FORBIDDEN_NEGATIVE_ACCOUNTS = {
    "TREASURY",
    "FOUNDER",
    "CREDIT",
    "INVESTMENT"
}

def enforce_no_negative_balances():
    with OmegaTransaction() as cur:
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
        if r["account_type"] in FORBIDDEN_NEGATIVE_ACCOUNTS and r["balance"] < 0:
            violations.append(r)

    if violations:
        print("❌ CONSTRAINT VIOLATION: NEGATIVE INSTITUTIONAL BALANCES")
        for v in violations:
            print(v)
        return {"status": "FAILED", "violations": violations}

    print("✅ ALL INSTITUTIONAL BALANCES VALID")
    return {"status": "OK", "violations": []}


if __name__ == "__main__":
    enforce_no_negative_balances()
