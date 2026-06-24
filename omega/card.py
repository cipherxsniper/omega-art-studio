
import os
import uuid
import random
import datetime
import psycopg2
from psycopg2 import Error

def luhn_checksum(card_number):
    digits = [int(d) for d in card_number]
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(divmod(d * 2, 10))
    return checksum % 10

def is_luhn_valid(card_number):
    return luhn_checksum(card_number) == 0

def generate_visa_card_number():
    while True:
        # Visa card numbers start with 4
        card_number = '4' + ''.join([str(random.randint(0, 9)) for _ in range(14)])
        # Calculate the checksum digit
        checksum_digit = (10 - luhn_checksum(card_number + '0')) % 10
        full_card_number = card_number + str(checksum_digit)
        if is_luhn_valid(full_card_number):
            return full_card_number

def generate_cvv():
    return ''.join([str(random.randint(0, 9)) for _ in range(3)])

def generate_expiry_date():
    # Expiry date 3-5 years from now
    today = datetime.date.today()
    future_date = today + datetime.timedelta(days=random.randint(3*365, 5*365))
    return future_date.strftime('%m/%y')

def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME', 'your_db_name'),
            user=os.getenv('DB_USER', 'your_db_user'),
            password=os.getenv('DB_PASSWORD', 'your_db_password'),
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432')
        )
        return conn
    except Error as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return None

def create_wallet(conn):
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO wallets DEFAULT VALUES RETURNING wallet_id;")
            wallet_id = cur.fetchone()[0]
            conn.commit()
            print(f"Wallet created with ID: {wallet_id}")
            return wallet_id
    except Error as e:
        print(f"Error creating wallet: {e}")
        conn.rollback()
        return None

def create_card(
    conn, wallet_id, card_number, expiry_date, cvv, cardholder_name, billing_zip_code
):
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO cards (
                    wallet_id, card_number, expiry_date, cvv, cardholder_name, billing_zip_code
                ) VALUES (%s, %s, %s, %s, %s, %s) RETURNING card_id;""",
                (
                    wallet_id,
                    card_number,
                    expiry_date,
                    cvv,
                    cardholder_name,
                    billing_zip_code,
                ),
            )
            card_id = cur.fetchone()[0]
            conn.commit()
            print(f"Card created with ID: {card_id}")
            return card_id
    except Error as e:
        print(f"Error creating card: {e}")
        conn.rollback()
        return None

def record_ledger_entry(
    conn, wallet_id, card_id, transaction_type, amount, description, idempotency_key
):
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO ledger_entries (
                    wallet_id, card_id, transaction_type, amount, description, idempotency_key
                ) VALUES (%s, %s, %s, %s, %s, %s) RETURNING entry_id;""",
                (
                    wallet_id,
                    card_id,
                    transaction_type,
                    amount,
                    description,
                    idempotency_key,
                ),
            )
            entry_id = cur.fetchone()[0]
            conn.commit()
            print(f"Ledger entry recorded: {entry_id}")
            return entry_id
    except Error as e:
        print(f"Error recording ledger entry: {e}")
        conn.rollback()
        return None

def authorize_transaction(conn, card_id, transaction_amount, idempotency_key):
    try:
        with conn.cursor() as cur:
            # Check for idempotency key first
            cur.execute(
                "SELECT attempt_id, status FROM authorization_attempts WHERE idempotency_key = %s;",
                (idempotency_key,)
            )
            existing_attempt = cur.fetchone()
            if existing_attempt:
                print(f"Transaction with idempotency key {idempotency_key} already processed. Status: {existing_attempt[1]}")
                return existing_attempt[1] == 'approved'

            cur.execute(
                "SELECT w.wallet_id, w.balance, c.status FROM cards c JOIN wallets w ON c.wallet_id = w.wallet_id WHERE c.card_id = %s;",
                (card_id,)
            )
            result = cur.fetchone()
            if not result:
                print("Card not found.")
                record_authorization_attempt(conn, card_id, transaction_amount, 'declined', 'card_not_found', idempotency_key)
                return False

            wallet_id, current_balance, card_status = result

            if card_status != 'active':
                print(f"Card is {card_status}.")
                record_authorization_attempt(conn, card_id, transaction_amount, 'declined', f'card_{card_status}', idempotency_key)
                return False

            if current_balance >= transaction_amount:
                # Approve transaction
                new_balance = current_balance - transaction_amount
                cur.execute(
                    "UPDATE wallets SET balance = %s WHERE wallet_id = %s;",
                    (new_balance, wallet_id)
                )
                record_ledger_entry(conn, wallet_id, card_id, 'DEBIT', transaction_amount, 'Card Authorization', idempotency_key)
                record_authorization_attempt(conn, card_id, transaction_amount, 'approved', 'sufficient_funds', idempotency_key)
                conn.commit()
                print("Transaction approved.")
                return True
            else:
                # Decline transaction
                record_authorization_attempt(conn, card_id, transaction_amount, 'declined', 'insufficient_funds', idempotency_key)
                conn.commit()
                print("Transaction declined: Insufficient funds.")
                return False
    except Error as e:
        print(f"Error during authorization: {e}")
        conn.rollback()
        record_authorization_attempt(conn, card_id, transaction_amount, 'declined', f'database_error: {e}', idempotency_key)
        return False

def record_authorization_attempt(conn, card_id, transaction_amount, status, reason, idempotency_key):
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO authorization_attempts (
                    card_id, transaction_amount, status, reason, idempotency_key
                ) VALUES (%s, %s, %s, %s, %s);""",
                (card_id, transaction_amount, status, reason, idempotency_key)
            )
            conn.commit()
    except Error as e:
        print(f"Error recording authorization attempt: {e}")
        conn.rollback()


if __name__ == "__main__":
    conn = get_db_connection()
    if not conn:
        exit(1)

    print("\n--- Generate New Virtual Card ---")

    # User Input
    first_name = input("Enter cardholder first name: ")
    last_name = input("Enter cardholder last name: ")
    cardholder_name = f"{first_name} {last_name}"
    billing_zip_code = ''.join([str(random.randint(0, 9)) for _ in range(5)]) # Random 5-digit zip code
    print(f"Generated billing zip code: {billing_zip_code}")

    # Generate card details
    card_number = generate_visa_card_number()
    cvv = generate_cvv()
    expiry_date = generate_expiry_date()

    # Create wallet and card
    wallet_id = create_wallet(conn)
    if wallet_id:
        card_id = create_card(
            conn, wallet_id, card_number, expiry_date, cvv, cardholder_name, billing_zip_code
        )
        if card_id:
            # Record initial credit to the wallet for testing purposes
            initial_credit_amount = 1000.00 # Example initial balance
            record_ledger_entry(
                conn, wallet_id, None, 'CREDIT', initial_credit_amount, 'Initial Wallet Funding', uuid.uuid4()
            )
            with conn.cursor() as cur:
                cur.execute("UPDATE wallets SET balance = %s WHERE wallet_id = %s;", (initial_credit_amount, wallet_id))
                conn.commit()
            print(f"Wallet {wallet_id} funded with {initial_credit_amount:.2f}")

            print("\n--- Your New Virtual Card Details ---")
            print(f"Cardholder Name: {cardholder_name}")
            print(f"Card Number: {card_number}")
            print(f"Expiry Date: {expiry_date}")
            print(f"CVV: {cvv}")
            print(f"Billing Zip Code: {billing_zip_code}")
            print(f"Associated Wallet ID: {wallet_id}")
            print(f"Card ID: {card_id}")

            # Example Authorization Attempt
            print("\n--- Example Authorization Attempt ---")
            test_transaction_amount = 50.00
            test_idempotency_key = uuid.uuid4()
            print(f"Attempting to authorize {test_transaction_amount:.2f} for card {card_id}...")
            if authorize_transaction(conn, card_id, test_transaction_amount, test_idempotency_key):
                print("Example transaction successful!")
            else:
                print("Example transaction failed.")

    conn.close()
