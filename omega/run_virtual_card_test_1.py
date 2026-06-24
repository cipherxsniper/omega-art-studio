import psycopg2
from omega_virtual_card import create_virtual_card, process_card_transaction

DB = {
    "dbname": "omega_bank",
    "user": "omega",
    "host": "localhost",
    "port": 5432
}

def run():
    conn = psycopg2.connect(**DB)

    wallet_id = "8fcaf9c3-24d1-4c4b-ad88-856576b8b6e9"

    print("\n[STEP 1] Issuing Virtual Card...\n")

    card = create_virtual_card(
        conn,
        wallet_id=wallet_id,
        spendable_limit=5000.00,
        idem_key="card-init-001"
    )

    print(card)

    print("\n[STEP 2] Running Real Transaction Simulation...\n")

    tx1 = process_card_transaction(
        conn,
        card_token=card["card_token"],
        amount=250.00,
        merchant="AMAZON_TEST",
        idem_key="tx-001"
    )

    print(tx1)

    tx2 = process_card_transaction(
        conn,
        card_token=card["card_token"],
        amount=1200.00,
        merchant="CLOUD_SERVICES",
        idem_key="tx-002"
    )

    print(tx2)

    conn.close()

if __name__ == "__main__":
    run()
