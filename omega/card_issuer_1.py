
import uuid
import datetime
import hmac
import hashlib
from decimal import Decimal
from typing import Optional, Dict, Any

from config import DatabasePool
from events import EventStore

class CardIssuer:
    def __init__(self, db_pool: DatabasePool, event_store: EventStore, bin_prefix: str = "8888"):
        self.db_pool = db_pool
        self.event_store = event_store
        self.bin_prefix = bin_prefix
        self.cvv_secret = "super_secret_cvv_key" # In a real system, this would be loaded securely

    def _luhn_checksum(self, card_number: str) -> int:
        digits = [int(d) for d in card_number]
        checksum = 0
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 0:  # Odd positions from the right
                checksum += digit
            else:  # Even positions from the right
                doubled_digit = digit * 2
                checksum += doubled_digit - 9 if doubled_digit > 9 else doubled_digit
        return checksum % 10

    def _generate_luhn_number(self, prefix: str, length: int) -> str:
        while True:
            # Generate random digits for the remaining part
            remaining_length = length - len(prefix) - 1 # -1 for the checksum digit
            random_digits = ''.join([str(uuid.uuid4().int % 10) for _ in range(remaining_length)])
            potential_card_number_base = prefix + random_digits
            
            # Calculate checksum for the potential base
            # Luhn algorithm works by adding a checksum digit to make the total sum divisible by 10
            # So we need to calculate what the checksum *should* be for the current base
            # to make the full number valid.
            
            # Create a temporary number with a '0' as the last digit to calculate the checksum
            temp_number = potential_card_number_base + '0'
            checksum = self._luhn_checksum(temp_number)
            
            # The actual checksum digit needed is (10 - checksum) % 10
            luhn_digit = (10 - checksum) % 10
            card_number = potential_card_number_base + str(luhn_digit)
            
            # Double check with the full number
            if self._luhn_checksum(card_number) == 0:
                return card_number

    def _generate_cvv(self, card_number: str, expiration_date: datetime.date) -> str:
        message = f"{card_number}-{expiration_date.strftime('%Y%m')}".encode('utf-8')
        h = hmac.new(self.cvv_secret.encode('utf-8'), message, hashlib.sha256)
        # Take first 3 digits of the hex digest as CVV
        return h.hexdigest()[:3]

    def issue_card(self, wallet_id: str, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        """Issues a new Omega card for a given wallet."""
        conn = self.db_pool.get_connection()
        try:
            with conn.cursor() as cur:
                # Generate card details
                card_number = self._generate_luhn_number(self.bin_prefix, 16)
                expiration_date = (datetime.date.today().replace(day=1) + datetime.timedelta(days=30*36)).replace(day=1) - datetime.timedelta(days=1) # 3 years from now, end of month
                cvv = self._generate_cvv(card_number, expiration_date)

                card_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO cards (id, wallet_id, card_number, cvv, expiration_date, status)
                    VALUES (%s, %s, %s, %s, %s, %s::card_status_type)
                    RETURNING id, wallet_id, card_number, expiration_date, status, created_at
                """, (card_id, wallet_id, card_number, cvv, expiration_date, 'ACTIVE'))
                row = cur.fetchone()

                self.event_store.append_event(
                    'CARD_ISSUED',
                    card_id,
                    {
                        "wallet_id": wallet_id,
                        "card_number_prefix": card_number[:6], # Store prefix for security
                        "expiration_date": expiration_date.strftime('%Y-%m'),
                        "status": 'ACTIVE'
                    },
                    idempotency_key=idempotency_key
                )
                conn.commit()
                return {
                    "id": row[0],
                    "wallet_id": row[1],
                    "card_number": row[2],
                    "expiration_date": row[3],
                    "status": row[4],
                    "created_at": row[5]
                }
        except Exception as e:
            conn.rollback()
            raise
        finally:
            self.db_pool.put_connection(conn)

    def get_card(self, card_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves card information."""
        conn = self.db_pool.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, wallet_id, card_number, expiration_date, status, created_at, updated_at
                    FROM cards
                    WHERE id = %s
                """, (card_id,))
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "id": row[0],
                    "wallet_id": row[1],
                    "card_number": row[2],
                    "expiration_date": row[3],
                    "status": row[4],
                    "created_at": row[5],
                    "updated_at": row[6]
                }
        finally:
            self.db_pool.put_connection(conn)

    def get_card_by_number(self, card_number: str) -> Optional[Dict[str, Any]]:
        """Retrieves card information by card number."""
        conn = self.db_pool.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, wallet_id, card_number, expiration_date, status, created_at, updated_at
                    FROM cards
                    WHERE card_number = %s
                """, (card_number,))
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "id": row[0],
                    "wallet_id": row[1],
                    "card_number": row[2],
                    "expiration_date": row[3],
                    "status": row[4],
                    "created_at": row[5],
                    "updated_at": row[6]
                }
        finally:
            self.db_pool.put_connection(conn)

    def set_card_status(self, card_id: str, status: str, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        """Updates the status of a card."""
        conn = self.db_pool.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE cards
                    SET status = %s::card_status_type
                    WHERE id = %s
                    RETURNING id, status, updated_at
                """, (status, card_id))
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"Card with ID {card_id} not found.")
                
                self.event_store.append_event(
                    'CARD_STATUS_UPDATED',
                    card_id,
                    {"new_status": status, "action": "UPDATE_STATUS"},
                    idempotency_key=idempotency_key
                )
                conn.commit()
                return {
                    "id": row[0],
                    "status": row[1],
                    "updated_at": row[2]
                }
        except Exception as e:
            conn.rollback()
            raise
        finally:
            self.db_pool.put_connection(conn)
