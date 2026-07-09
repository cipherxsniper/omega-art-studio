
import uuid
from typing import Optional, Dict, Any
from decimal import Decimal

from config import DatabasePool
from events import EventStore

class MerchantSystem:
    def __init__(self, db_pool: DatabasePool, event_store: EventStore):
        self.db_pool = db_pool
        self.event_store = event_store

    def register_merchant(self, name: str, merchant_id: str, api_key: str, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        """Registers a new merchant."""
        conn = self.db_pool.get_connection()
        try:
            with conn.cursor() as cur:
                merchant_uuid = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO merchants (id, name, merchant_id, api_key, status)
                    VALUES (%s, %s, %s, %s, %s::merchant_status_type)
                    RETURNING id, name, merchant_id, status, created_at
                """, (merchant_uuid, name, merchant_id, api_key, 'ACTIVE'))
                row = cur.fetchone()

                self.event_store.append_event(
                    'MERCHANT_REGISTERED',
                    merchant_uuid,
                    {
                        "name": name,
                        "merchant_id": merchant_id,
                        "status": 'ACTIVE'
                    },
                    idempotency_key=idempotency_key
                )
                conn.commit()
                return {
                    "id": row[0],
                    "name": row[1],
                    "merchant_id": row[2],
                    "status": row[3],
                    "created_at": row[4]
                }
        except Exception as e:
            conn.rollback()
            raise
        finally:
            self.db_pool.put_connection(conn)

    def get_merchant(self, merchant_uuid: str) -> Optional[Dict[str, Any]]:
        """Retrieves merchant information by internal UUID."""
        conn = self.db_pool.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, name, merchant_id, status, created_at, updated_at
                    FROM merchants
                    WHERE id = %s
                """, (merchant_uuid,))
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "id": row[0],
                    "name": row[1],
                    "merchant_id": row[2],
                    "status": row[3],
                    "created_at": row[4],
                    "updated_at": row[5]
                }
        finally:
            self.db_pool.put_connection(conn)

    def get_merchant_by_merchant_id(self, merchant_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves merchant information by external merchant_id."""
        conn = self.db_pool.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, name, merchant_id, status, created_at, updated_at
                    FROM merchants
                    WHERE merchant_id = %s
                """, (merchant_id,))
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "id": row[0],
                    "name": row[1],
                    "merchant_id": row[2],
                    "status": row[3],
                    "created_at": row[4],
                    "updated_at": row[5]
                }
        finally:
            self.db_pool.put_connection(conn)

    def create_payment_request(self, merchant_uuid: str, amount: Decimal, currency: str = 'USD', description: str = '', idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        """Creates a payment request for a merchant."""
        conn = self.db_pool.get_connection()
        try:
            with conn.cursor() as cur:
                payment_request_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO payment_requests (id, merchant_id, amount, currency, description, status)
                    VALUES (%s, %s, %s, %s, %s, %s::payment_request_status_type)
                    RETURNING id, merchant_id, amount, currency, description, status, created_at
                """, (payment_request_id, merchant_uuid, amount, currency, description, 'PENDING'))
                row = cur.fetchone()

                self.event_store.append_event(
                    'PAYMENT_REQUEST_CREATED',
                    payment_request_id,
                    {
                        "merchant_id": merchant_uuid,
                        "amount": str(amount),
                        "currency": currency,
                        "description": description,
                        "status": 'PENDING'
                    },
                    idempotency_key=idempotency_key
                )
                conn.commit()
                return {
                    "id": row[0],
                    "merchant_id": row[1],
                    "amount": row[2],
                    "currency": row[3],
                    "description": row[4],
                    "status": row[5],
                    "created_at": row[6]
                }
        except Exception as e:
            conn.rollback()
            raise
        finally:
            self.db_pool.put_connection(conn)

    def generate_invoice(self, payment_request_details: Dict[str, Any]) -> str:
        """Generates a simple text-based invoice from payment request details."""
        invoice = f"""
        --- INVOICE ---
        Invoice ID: {payment_request_details.get('id', 'N/A')}
        Merchant ID: {payment_request_details.get('merchant_id', 'N/A')}
        Amount: {payment_request_details.get('amount', 'N/A')} {payment_request_details.get('currency', 'N/A')}
        Description: {payment_request_details.get('description', 'N/A')}
        Status: {payment_request_details.get('status', 'N/A')}
        Date: {payment_request_details.get('created_at', 'N/A')}
        ----------------
        """
        return invoice

    def generate_receipt(self, payment_transaction_details: Dict[str, Any]) -> str:
        """Generates a simple text-based receipt from payment transaction details."""
        receipt = f"""
        --- RECEIPT ---
        Transaction ID: {payment_transaction_details.get('id', 'N/A')}
        Payment Request ID: {payment_transaction_details.get('payment_request_id', 'N/A')}
        Wallet ID: {payment_transaction_details.get('wallet_id', 'N/A')}
        Amount: {payment_transaction_details.get('amount', 'N/A')} {payment_transaction_details.get('currency', 'N/A')}
        Type: {payment_transaction_details.get('transaction_type', 'N/A')}
        Status: {payment_transaction_details.get('status', 'N/A')}
        Date: {payment_transaction_details.get('created_at', 'N/A')}
        ----------------
        """
        return receipt
