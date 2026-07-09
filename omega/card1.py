
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
        card_number = '16' + ''.join([str(random.randint(0, 9)) for _ in range(14)])
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
        conn.autocommit = False # Ensure transactions are managed manually
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

def record_transaction_and_entries(
    conn, wallet_id, card_id, transaction_type, amount, description, idempotency_key, merchant_wallet_id=None
):
    try:
        with conn.cursor() as cur:
            # Check for existing transaction with idempotency key
            cur.execute(
                "SELECT transaction_id FROM ledger_transactions WHERE idempotency_key = %s;",
                (idempotency_key,)
            )
            existing_transaction = cur.fetchone()
            if existing_transaction:
                print(f"Transaction with idempotency key {idempotency_key} already exists.")
                return existing_transaction[0]

            # Create ledger transaction
            cur.execute(
                "INSERT INTO ledger_transactions (idempotency_key, description) VALUES (%s, %s) RETURNING transaction_id;",
                (idempotency_key, description)
            )
            transaction_id = cur.fetchone()[0]

            # Record DEBIT entry for the user's wallet
            cur.execute(
                """INSERT INTO ledger_entries (
                    transaction_id, wallet_id, card_id, direction, amount, description
                ) VALUES (%s, %s, %s, %s, %s, %s);""",
                (
                    transaction_id,
                    wallet_id,
                    card_id,
                    'DEBIT',
                    amount,
                    description,
                ),
            )

            # Record CREDIT entry for the merchant/system wallet (double-entry)
            if merchant_wallet_id:
                cur.execute(
                    """INSERT INTO ledger_entries (
                        transaction_id, wallet_id, card_id, direction, amount, description
                    ) VALUES (%s, %s, %s, %s, %s, %s);""",
                    (
                        transaction_id,
                        merchant_wallet_id,
                        card_id, # Card ID can be associated with the merchant side too for audit
                        'CREDIT',
                        amount,
                        description,
                    ),
                )
            else:
                # For initial funding or internal credits, a single entry might be acceptable
                # but for true double-entry, there should always be a balancing entry.
                # For simplicity in this sandbox, we'll allow single entry for initial credit.
                pass

            conn.commit()
            print(f"Ledger transaction recorded: {transaction_id}")
            return transaction_id
    except Error as e:
        print(f"Error recording ledger transaction: {e}")
        conn.rollback()
        return None

def get_wallet_balance(conn, wallet_id):
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT SUM(CASE WHEN direction = 'CREDIT' THEN amount ELSE -amount END) FROM ledger_entries WHERE wallet_id = %s;""",
                (wallet_id,)
            )
            balance = cur.fetchone()[0]
            return balance if balance is not None else 0.00
    except Error as e:
        print(f"Error calculating wallet balance: {e}")
        return 0.00

def authorize_transaction(conn, card_id, transaction_amount, idempotency_key, merchant_wallet_id):
    transaction_id = None
    try:
        with conn.cursor() as cur:
            # Check for idempotency key for the authorization attempt itself
            cur.execute(
                "SELECT attempt_id, status FROM authorization_attempts WHERE idempotency_key = %s;",
                (idempotency_key,)
            )
            existing_attempt = cur.fetchone()
            if existing_attempt:
                print(f"Authorization attempt with idempotency key {idempotency_key} already processed. Status: {existing_attempt[1]}")
                return existing_attempt[1] == 'approved'

            # Acquire wallet-level lock using pg_advisory_xact_lock
            # First, get the wallet_id associated with the card
            cur.execute("SELECT wallet_id, status FROM cards WHERE card_id = %s;", (card_id,))
            card_info = cur.fetchone()
            if not card_info:
                print("Card not found.")
                record_authorization_attempt(conn, card_id, None, transaction_amount, 'declined', 'card_not_found', idempotency_key)
                conn.commit()
                return False

            wallet_id, card_status = card_info

            # Use pg_advisory_xact_lock for wallet-level locking
            cur.execute("SELECT pg_advisory_xact_lock(%s);", (int(uuid.UUID(str(wallet_id)).int % (2**63 - 1)),))

            if card_status != 'active':
                print(f"Card is {card_status}.")
                record_authorization_attempt(conn, card_id, None, transaction_amount, 'declined', f'card_{card_status}', idempotency_key)
                conn.commit()
                return False

            current_balance = get_wallet_balance(conn, wallet_id)

            if current_balance >= transaction_amount:
                # Approve transaction
                description = f'Card Authorization for {transaction_amount:.2f}'
                transaction_id = record_transaction_and_entries(
                    conn, wallet_id, card_id, 'DEBIT', transaction_amount, description, idempotency_key, merchant_wallet_id
                )
                if transaction_id:
                    record_authorization_attempt(conn, card_id, transaction_id, transaction_amount, 'approved', 'sufficient_funds', idempotency_key)
                    conn.commit()
                    print("Transaction approved.")
                    return True
                else:
                    # Transaction recording failed, rollback authorization attempt as well
                    conn.rollback()
                    print("Transaction recording failed.")
                    record_authorization_attempt(conn, card_id, None, transaction_amount, 'declined', 'ledger_write_failed', idempotency_key)
                    conn.commit()
                    return False
            else:
                # Decline transaction
                record_authorization_attempt(conn, card_id, None, transaction_amount, 'declined', 'insufficient_funds', idempotency_key)
                conn.commit()
                print("Transaction declined: Insufficient funds.")
                return False
    except Error as e:
        print(f"Error during authorization: {e}")
        conn.rollback()
        record_authorization_attempt(conn, card_id, transaction_id, transaction_amount, 'declined', f'database_error: {e}', idempotency_key)
        conn.commit()
        return False

def record_authorization_attempt(conn, card_id, transaction_id, requested_amount, status, reason, idempotency_key):
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO authorization_attempts (
                    card_id, transaction_id, requested_amount, status, reason, idempotency_key
                ) VALUES (%s, %s, %s, %s, %s, %s);""",
                (card_id, transaction_id, requested_amount, status, reason, idempotency_key)
            )
            # No commit here, as it's part of a larger transaction or committed by the caller
    except Error as e:
        print(f"Error recording authorization attempt: {e}")
        # This rollback is only for the attempt recording, not the main transaction
        conn.rollback()


if __name__ == "__main__":
    conn = get_db_connection()
    if not conn:
        exit(1)

    # Ensure a merchant wallet exists for double-entry accounting
    merchant_wallet_id = os.getenv('MERCHANT_WALLET_ID')
    if not merchant_wallet_id:
        print("Creating a default merchant wallet...")
        merchant_wallet_id = create_wallet(conn)
        if merchant_wallet_id:
            print(f"Please set MERCHANT_WALLET_ID environment variable to {merchant_wallet_id} for future runs.")
            os.environ['MERCHANT_WALLET_ID'] = str(merchant_wallet_id) # Set for current session
        else:
            print("Failed to create merchant wallet. Exiting.")
            conn.close()
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
            # Record initial credit to the user's wallet
            initial_credit_amount = 1000.00 # Example initial balance
            initial_funding_idempotency_key = uuid.uuid4()
            print(f"Funding wallet {wallet_id} with {initial_credit_amount:.2f}...")
            record_transaction_and_entries(
                conn, wallet_id, None, 'CREDIT', initial_credit_amount, 'Initial Wallet Funding', initial_funding_idempotency_key, merchant_wallet_id
            )
            # For initial funding, we are crediting the user's wallet and debiting the merchant wallet.
            # This simulates funds coming *from* the bank/system *to* the user.
            # The record_transaction_and_entries function already handles the double entry.

            print("\n--- Your New Virtual Card Details ---")
            print(f"Cardholder Name: {cardholder_name}")
            print(f"Card Number: {card_number}")
            print(f"Expiry Date: {expiry_date}")
            print(f"CVV: {cvv}")
            print(f"Billing Zip Code: {billing_zip_code}")
            print(f"Associated Wallet ID: {wallet_id}")
            print(f"Card ID: {card_id}")
            print(f"Current Wallet Balance: {get_wallet_balance(conn, wallet_id):.2f}")

            # Example Authorization Attempt
            print("\n--- Example Authorization Attempt ---")
            test_transaction_amount = 550.00
            test_idempotency_key = uuid.uuid4()
            print(f"Attempting to authorize {test_transaction_amount:.2f} for card {card_id}...")
            if authorize_transaction(conn, card_id, test_transaction_amount, test_idempotency_key, merchant_wallet_id):
                print("Example transaction successful!")
            else:
                print("Example transaction failed.")
            print(f"Wallet Balance after attempt: {get_wallet_balance(conn, wallet_id):.2f}")

            print("\n--- Another Example Authorization Attempt (should fail due to insufficient funds) ---")
            test_transaction_amount_fail = 600.00
            test_idempotency_key_fail = uuid.uuid4()
            print(f"Attempting to authorize {test_transaction_amount_fail:.2f} for card {card_id}...")
            if authorize_transaction(conn, card_id, test_transaction_amount_fail, test_idempotency_key_fail, merchant_wallet_id):
                print("Second example transaction successful!")
            else:
                print("Second example transaction failed (as expected).")
            print(f"Wallet Balance after second attempt: {get_wallet_balance(conn, wallet_id):.2f}")

            print("\n--- Idempotency Test (should return original result) ---")
            print(f"Re-attempting to authorize {test_transaction_amount:.2f} for card {card_id} with same idempotency key...")
            if authorize_transaction(conn, card_id, test_transaction_amount, test_idempotency_key, merchant_wallet_id):
                print("Idempotency test successful (original transaction result returned).")
            else:
                print("Idempotency test failed.")
            print(f"Wallet Balance after idempotency test: {get_wallet_balance(conn, wallet_id):.2f}")

    conn.close()
