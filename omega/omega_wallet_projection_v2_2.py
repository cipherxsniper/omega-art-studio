import psycopg2
from decimal import Decimal
from collections import defaultdict

DB_NAME = "omega_bank"
DB_USER = "omega"


def fetch_postings():
    conn = psycopg2.connect(database=DB_NAME, user=DB_USER)
    cur = conn.cursor()

    # Pull raw postings without assumptions
    cur.execute("""
        SELECT *
        FROM ledger_postings
    """)

    rows = cur.fetchall()

    # Get column index mapping safely
    colnames = [desc[0] for desc in cur.description]

    conn.close()

    return rows, colnames


def normalize(rows, cols):
    """
    Schema-agnostic double-entry projection.
    """

    balances = defaultdict(Decimal)

    for row in rows:

        row_map = dict(zip(cols, row))

        # REQUIRED SAFE FIELDS ONLY
        account_id = row_map.get("account_id")

        if account_id is None:
            continue

        # find amount-like field
        amount = (
            row_map.get("amount")
            or row_map.get("value")
            or row_map.get("delta")
            or 0
        )

        amount = Decimal(str(amount))

        # detect direction safely
        direction = str(
            row_map.get("direction")
            or row_map.get("type")
            or row_map.get("side")
            or "CREDIT"
        ).upper()

        # double-entry logic
        if direction in ("DEBIT", "DR", "OUT", "WITHDRAWAL"):
            balances[account_id] -= amount
        else:
            balances[account_id] += amount

    return balances


def get_wallet_balances():
    rows, cols = fetch_postings()
    return normalize(rows, cols)


def get_wallet_balance(account_id):
    return get_wallet_balances().get(account_id, Decimal("0.0"))


if __name__ == "__main__":
    print("💰 WALLET PROJECTION (FULL SCHEMA AGNOSTIC MODE)")
    balances = get_wallet_balances()

    for k, v in balances.items():
        print(k, "=>", v)
