import psycopg2
import uuid
from datetime import datetime

DB_NAME = "omega_bank"
DB_USER = "omega"


# =========================================================
# LEGACY EVENT NORMALIZER v1
# =========================================================
# Repairs pre-freeze events so:
#
# - replay becomes deterministic
# - projection becomes deterministic
# - all historical events align to schema freeze
# =========================================================


def get_connection():

    return psycopg2.connect(
        database=DB_NAME,
        user=DB_USER
    )


def normalize_legacy_events():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            event_id,
            aggregate_type,
            timestamp,
            merchant_id,
            wallet_id,
            amount,
            currency
        FROM omega_events
        """
    )

    rows = cur.fetchall()

    repaired = 0

    for row in rows:

        event_id = row[0]

        aggregate_type = row[1]
        timestamp = row[2]
        merchant_id = row[3]
        wallet_id = row[4]
        amount = row[5]
        currency = row[6]

        changed = False

        # ==========================================
        # AGGREGATE TYPE
        # ==========================================

        if not aggregate_type:

            aggregate_type = "PAYMENT"
            changed = True

        # ==========================================
        # TIMESTAMP
        # ==========================================

        if not timestamp:

            timestamp = datetime.utcnow()
            changed = True

        # ==========================================
        # MERCHANT ID
        # ==========================================

        if not merchant_id:

            merchant_id = "omega_legacy"
            changed = True

        # ==========================================
        # WALLET ID
        # ==========================================

        if not wallet_id:

            wallet_id = uuid.UUID(
                "00000000-0000-0000-0000-000000000000"
            )

            changed = True

        # ==========================================
        # AMOUNT
        # ==========================================

        if amount is None:

            amount = 0.00
            changed = True

        # ==========================================
        # CURRENCY
        # ==========================================

        if not currency:

            currency = "USD"
            changed = True

        # ==========================================
        # UPDATE
        # ==========================================

        if changed:

            cur.execute(
                """
                UPDATE omega_events
                SET
                    aggregate_type = %s,
                    timestamp = %s,
                    merchant_id = %s,
                    wallet_id = %s,
                    amount = %s,
                    currency = %s
                WHERE event_id = %s
                """,
                (
                    aggregate_type,
                    timestamp,
                    merchant_id,
                    str(wallet_id),
                    amount,
                    currency,
                    event_id
                )
            )

            repaired += 1

    conn.commit()

    cur.close()
    conn.close()

    return repaired


if __name__ == "__main__":

    repaired = normalize_legacy_events()

    print("✅ LEGACY EVENTS NORMALIZED")
    print(f"REPAIRED: {repaired}")

