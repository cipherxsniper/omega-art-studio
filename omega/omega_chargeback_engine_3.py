import uuid
import psycopg2
from decimal import Decimal

DB="omega_bank"
USER="omega"

def conn():
    return psycopg2.connect(
        dbname=DB,
        user=USER
    )

def issue_chargeback(
    auth_id,
    wallet_id,
    merchant,
    amount,
    network,
    reason_code
):

    c = conn()

    with c.cursor() as cur:

        chargeback_id = str(uuid.uuid4())

        cur.execute("""
            INSERT INTO chargeback_cases (
                id,
                auth_id,
                wallet_id,
                merchant,
                amount,
                network,
                reason_code,
                status
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            chargeback_id,
            auth_id,
            wallet_id,
            merchant,
            amount,
            network,
            reason_code,
            "OPEN"
        ))

        cur.execute("""
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
                %s,
                'DEBIT',
                %s,
                %s,
                NOW()
            )
        """, (
            wallet_id,
            amount,
            f"chargeback-{chargeback_id}"
        ))

        cur.execute("""
            UPDATE wallets
            SET settled_balance = settled_balance - %s
            WHERE id=%s
        """, (
            amount,
            wallet_id
        ))

    c.commit()
    c.close()

    return {
        "status": "CHARGEBACK_OPENED",
        "chargeback_id": chargeback_id,
        "amount": float(amount)
    }

if __name__ == "__main__":

    result = issue_chargeback(
        "170ed881-bb6b-4e32-af22-c6579b66b9ea",
        "fe881e17-8b24-42f4-ba4f-c1ce38770b51",
        "OMEGA_NETWORK_STORE",
        Decimal("125.00"),
        "MASTERCARD",
        "4837"
    )

    print(result)

