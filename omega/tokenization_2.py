
import uuid
from typing import Optional, Dict, Any

from config import DatabasePool
from events import EventStore

class TokenizationEngine:
    def __init__(self, db_pool: DatabasePool, event_store: EventStore):
        self.db_pool = db_pool
        self.event_store = event_store

    def generate_token(self, card_id: str, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        """Generates a new token for a given card."""
        conn = self.db_pool.get_connection()
        try:
            with conn.cursor() as cur:
                token_value = str(uuid.uuid4()) # Simple UUID for token value
                token_id = str(uuid.uuid4())

                cur.execute("""
                    INSERT INTO tokens (id, card_id, token_value, status)
                    VALUES (%s, %s, %s, %s::token_status_type)
                    RETURNING id, card_id, token_value, status, created_at
                """, (token_id, card_id, token_value, 'ACTIVE'))
                row = cur.fetchone()

                self.event_store.append_event(
                    'TOKEN_ISSUED',
                    token_id,
                    {
                        "card_id": card_id,
                        "token_value_prefix": token_value[:8], # Store prefix for security
                        "status": 'ACTIVE'
                    },
                    idempotency_key=idempotency_key
                )
                conn.commit()
                return {
                    "id": row[0],
                    "card_id": row[1],
                    "token_value": row[2],
                    "status": row[3],
                    "created_at": row[4]
                }
        except Exception as e:
            conn.rollback()
            raise
        finally:
            self.db_pool.put_connection(conn)

    def get_token(self, token_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves token information."""
        conn = self.db_pool.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, card_id, token_value, status, created_at, updated_at
                    FROM tokens
                    WHERE id = %s
                """, (token_id,))
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "id": row[0],
                    "card_id": row[1],
                    "token_value": row[2],
                    "status": row[3],
                    "created_at": row[4],
                    "updated_at": row[5]
                }
        finally:
            self.db_pool.put_connection(conn)

    def get_token_by_value(self, token_value: str) -> Optional[Dict[str, Any]]:
        """Retrieves token information by token value."""
        conn = self.db_pool.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, card_id, token_value, status, created_at, updated_at
                    FROM tokens
                    WHERE token_value = %s
                """, (token_value,))
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "id": row[0],
                    "card_id": row[1],
                    "token_value": row[2],
                    "status": row[3],
                    "created_at": row[4],
                    "updated_at": row[5]
                }
        finally:
            self.db_pool.put_connection(conn)

    def set_token_status(self, token_id: str, status: str, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        """Updates the status of a token."""
        conn = self.db_pool.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE tokens
                    SET status = %s::token_status_type
                    WHERE id = %s
                    RETURNING id, status, updated_at
                """, (status, token_id))
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"Token with ID {token_id} not found.")
                
                self.event_store.append_event(
                    'TOKEN_STATUS_UPDATED',
                    token_id,
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
