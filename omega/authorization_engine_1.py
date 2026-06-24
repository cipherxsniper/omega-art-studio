
import uuid
from decimal import Decimal
from typing import Optional, Dict, Any

from config import DatabasePool
from events import EventStore
from wallets import WalletManager
from credit import CreditIssuer
from risk_engine import RiskEngine

class AuthorizationEngine:
    def __init__(self, db_pool: DatabasePool, event_store: EventStore, wallet_manager: WalletManager, credit_issuer: CreditIssuer, risk_engine: RiskEngine):
        self.db_pool = db_pool
        self.event_store = event_store
        self.wallet_manager = wallet_manager
        self.credit_issuer = credit_issuer
        self.risk_engine = risk_engine

    def authorize_payment(self, payment_request_id: str, wallet_id: str, card_id: Optional[str] = None, token_id: Optional[str] = None, amount: Decimal, currency: str, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        """Authorizes a payment request, checking ledger state and risk."""
        conn = self.db_pool.get_connection()
        try:
            with conn.cursor() as cur:
                # 1. Check idempotency key for the overall authorization process
                if idempotency_key:
                    cur.execute("SELECT id FROM payment_transactions WHERE idempotency_key = %s", (idempotency_key,))
                    if cur.fetchone():
                        conn.rollback()
                        raise ValueError(f"Payment transaction with idempotency key {idempotency_key} already exists.")

                # 2. Identify wallet and check status
                wallet = self.wallet_manager.get_wallet(wallet_id)
                if not wallet or wallet["status"] != "ACTIVE":
                    self._record_decline_event(payment_request_id, wallet_id, amount, currency, "FROZEN_OR_INACTIVE_WALLET", idempotency_key)
                    raise ValueError("Wallet is frozen or inactive.")

                # 3. Check credit line and exposure
                credit_line = self.credit_issuer.get_credit_line(wallet_id)
                if not credit_line or credit_line["status"] != "ACTIVE":
                    self._record_decline_event(payment_request_id, wallet_id, amount, currency, "NO_ACTIVE_CREDIT_LINE", idempotency_key)
                    raise ValueError("No active credit line for wallet.")

                available_credit = credit_line["credit_limit"] - credit_line["used_credit"]
                if amount > available_credit:
                    self._record_decline_event(payment_request_id, wallet_id, amount, currency, "INSUFFICIENT_FUNDS", idempotency_key)
                    raise ValueError("Insufficient funds.")

                # 4. Evaluate risk (simplified for now, actual risk engine would be more complex)
                # For now, we'll just check the risk score from the credit line
                if credit_line["risk_score"] > Decimal("75.00"): # Example threshold
                    self._record_decline_event(payment_request_id, wallet_id, amount, currency, "HIGH_RISK_SCORE", idempotency_key)
                    raise ValueError("Transaction declined due to high risk.")

                # 5. If all checks pass, create a reservation (hold funds)
                # This is a 'soft' hold on the credit line, to be settled later
                updated_credit_line = self.credit_issuer.update_credit_usage(
                    wallet_id, amount, "CREDIT_USAGE", f"Reservation for payment request {payment_request_id}", idempotency_key=idempotency_key
                )

                # Record the authorization event and payment transaction
                event_id = self.event_store.append_event(
                    'PAYMENT_AUTHORIZED',
                    wallet_id,
                    {
                        "payment_request_id": payment_request_id,
                        "amount": str(amount),
                        "currency": currency,
                        "status": "AUTHORIZED",
                        "used_credit_after_auth": str(updated_credit_line["used_credit"])
                    },
                    idempotency_key=idempotency_key
                )

                cur.execute("""
                    INSERT INTO payment_transactions (id, payment_request_id, wallet_id, card_id, token_id, event_id, amount, currency, transaction_type, status, idempotency_key)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::payment_transaction_type, %s::payment_transaction_status, %s)
                    RETURNING id, status, created_at
                """, (str(uuid.uuid4()), payment_request_id, wallet_id, card_id, token_id, event_id, amount, currency, 'AUTHORIZATION', 'APPROVED', idempotency_key))
                transaction_row = cur.fetchone()

                # Update payment request status to COMPLETED (or RESERVED if we want a separate status)
                cur.execute("""
                    UPDATE payment_requests
                    SET status = %s::payment_request_status_type
                    WHERE id = %s
                """, ("COMPLETED", payment_request_id))

                conn.commit()
                return {
                    "transaction_id": transaction_row[0],
                    "status": transaction_row[1],
                    "message": "Payment authorized and funds reserved."
                }
        except ValueError as ve:
            conn.rollback()
            # Re-raise the ValueError after rollback
            raise ve
        except Exception as e:
            conn.rollback()
            self._record_decline_event(payment_request_id, wallet_id, amount, currency, f"AUTHORIZATION_ERROR: {str(e)}", idempotency_key)
            raise
        finally:
            self.db_pool.put_connection(conn)

    def _record_decline_event(self, payment_request_id: str, wallet_id: str, amount: Decimal, currency: str, reason: str, idempotency_key: Optional[str] = None):
        """Records a payment decline event and transaction."""
        conn = self.db_pool.get_connection()
        try:
            with conn.cursor() as cur:
                event_id = self.event_store.append_event(
                    'PAYMENT_DECLINED',
                    wallet_id,
                    {
                        "payment_request_id": payment_request_id,
                        "amount": str(amount),
                        "currency": currency,
                        "reason": reason,
                        "status": "DECLINED"
                    },
                    idempotency_key=idempotency_key # Use the same idempotency key for the decline event
                )
                cur.execute("""
                    INSERT INTO payment_transactions (id, payment_request_id, wallet_id, event_id, amount, currency, transaction_type, status, idempotency_key)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::payment_transaction_type, %s::payment_transaction_status, %s)
                    RETURNING id, status, created_at
                """, (str(uuid.uuid4()), payment_request_id, wallet_id, event_id, amount, currency, 'DECLINE', 'DECLINED', idempotency_key))
                conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error recording decline event: {e}") # Log error, but don't re-raise to avoid masking original decline reason
        finally:
            self.db_pool.put_connection(conn)
