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
future_date = today + datetime.timedelta(days=random.randint(3365, 5365))
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

def create_card_and_token(
conn, wallet_id, card_number, expiry_date, cvv, cardholder_name, billing_zip_code
):
try:
with conn.cursor() as cur:
# Create wallet_payment_token entry
cur.execute(
"INSERT INTO wallet_payment_tokens (wallet_id, token, token_type) VALUES (%s, %s, %s) RETURNING token_id;",
(wallet_id, card_number, 'card'),
)
token_id = cur.fetchone()[0]
