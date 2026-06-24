s import EventStore
from credit import CreditIssuer
from treasury import TreasuryCoordinator

class SettlementEngine:
    def __init__(self, db_pool: DatabasePool, event_store: EventStore, credit_issuer: CreditIssuer, treasury_coordinator: TreasuryCoordinator):
        self.db_pool = db_pool
        self.event_store = event_store
        self.credit_issuer = credit_issuer
        self.treasury_coordinator = treasury_coordinator

    def settle_payment(self, payment_transaction_id: str, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        """Settles a previously authorized payment, converting reservation to final transfer."""
        conn = self.db_pool.get_connection()
        try:
            with conn.cursor() as cur:
                # 1. Retrieve the authorization transaction
                cur.execute("""
                    SELECT id, payment_request_id, wallet_id, amount, currency, transaction_type, status, idempotency_key
                    FROM payment_transactions
                    WHERE id = %s AND transaction_type = %s::payment_transaction_type AND status = %s::payment_transaction_status
                """, (payment_transaction_id, 'AUTHORIZATION', 'APPROVED'))
                auth_transaction = cur.fetchone()

                if not auth_transaction:
                    raise ValueError(f"Authorization transaction {payment_transaction_id} not found or not in APPROVED state.")
                
                # Unpack auth_transaction details
                auth_id, payment_request_id, wallet_id, amount, currency, _, _, auth_idempotency_key = auth_transaction

                # 2. Check for idempotency key for the settlement process
                if idempotency_key:
                    cur.execute("SELECT id FROM payment_transactions WHERE idempotency_key = %s", (idempotency_key,))
                    if cur.fetchone():
                        conn.rollback()
                        raise ValueError(f"Settlement transaction with idempotency key {idempotency_key} already exists.")

                # 3. Perform actual fund transfer/settlement logic
                # In this model, 'CREDIT_USAGE' already represents the reservation.
                # Settlement means confirming this usage and potentially moving funds from treasury to merchant.
                # For now, we'll assume the 'CREDIT_USAGE' in credit_lines is the reservation.
                # The actual transfer of funds from treasury to merchant would happen here.
                # This example will simulate by updating the payment_transaction status.

                # Example: Move funds from a general treasury reserve to cover the settlement
                # This assumes a 'general_settlement_reserve' exists
                # Note: TreasuryCoordinator expects a raw cursor, not the pool. This is a known inconsistency.
                # For now, we'll simulate the treasury interaction or assume it's handled externally.
                # self.treasury_coordinator.release_credit_from_reserve("general_settlement_reserve", amount, idempotency_key=idempotency_key)

                # 4. Record the settlement event
                event_id = self.event_store.append_event(
                    'PAYMENT_SETTLED',
                    wallet_id, # Entity ID could be wallet, or a specific settlement account
                    {
                        "payment_transaction_id": auth_id,
                        "payment_request_id": payment_request_id,
                        "amount": str(amount),
                        "currency": currency,
                        "status": "SETTLED"
                    },
                    idempotency_key=idempotency_key
                )

                # 5. Update the original authorization transaction status to SETTLED
                cur.execute("""
                    UPDATE payment_transactions
                    SET status = %s::payment_transaction_status, updated_at = NOW()
                    WHERE id = %s
                    RETURNING id, status, updated_at
                """, ('SETTLED', auth_id))
                updated_auth_row = cur.fetchone()

                # 6. Insert a new payment_transaction record for settlement (optional, but good for audit trail)
                cur.execute("""
                    INSERT INTO payment_transactions (id, payment_request_id, wallet_id, event_id, amount, currency, transaction_type, status, idempotency_key)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::payment_transaction_type, %s::payment_transaction_status, %s)
                    RETURNING id, status, created_at
                """, (str(uuid.uuid4()), payment_request_id, wallet_id, event_id, amount, currency, 'SETTLEMENT', 'SETTLED', idempotency_key))
                settlement_row = cur.fetchone()

                conn.commit()
                return {
                    "settlement_transaction_id": settlement_row[0],
                    "original_auth_id": updated_auth_row[0],
                    "status": updated_auth_row[1],
                    "message": "Payment settled successfully."
                }
        except Exception as e:
            conn.rollback()
            raise
        finally:
            self.db_pool.put_connection(conn)

    def refund_payment(self, payment_transaction_id: str, refund_amount: Decimal, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        """Refunds a settled payment."""
        conn = self.db_pool.get_connection()
        try:
            with conn.cursor() as cur:
                # 1. Retrieve the settled transaction
                cur.execute("""
                    SELECT id, payment_request_id, wallet_id, amount, currency, transaction_type, status, idempotency_key
                    FROM payment_transactions
                    WHERE id = %s AND status = %s::payment_transaction_status
                """, (payment_transaction_id, 'SETTLED'))
                settled_transaction = cur.fetchone()

                if not settled_transaction:
                    raise ValueError(f"Settled transaction {payment_transaction_id} not found or not in SETTLED state.")
                
                # Unpack settled_transaction details
                settled_id, payment_request_id, wallet_id, original_amount, currency, _, _, settled_idempotency_key = settled_transaction

                if refund_amount <= 0 or refund_amount > original_amount:
                    raise ValueError("Invalid refund amount.")

                # 2. Check for idempotency key for the refund process
                if idempotency_key:
                    cur.execute("SELECT id FROM payment_transactions WHERE idempotency_key = %s", (idempotency_key,))
                    if cur.fetchone():
                        conn.rollback()
                        raise ValueError(f"Refund transaction with idempotency key {idempotency_key} already exists.")

                # 3. Reverse the credit usage
                self.credit_issuer.update_credit_usage(
                    wallet_id, refund_amount, "CREDIT_REPAYMENT", f"Refund for transaction {payment_transaction_id}", idempotency_key=idempotency_key
                )

                # 4. Record the refund event
                event_id = self.event_store.append_event(
                    'PAYMENT_REFUNDED',
                    wallet_id,
                    {
                        "payment_transaction_id": settled_id,
                        "payment_request_id": payment_request_id,
                        "refund_amount": str(refund_amount),
                        "currency": currency,
                        "status": "REFUNDED"
                    },
                    idempotency_key=idempotency_key
                )

                # 5. Insert a new payment_transaction record for refund
                cur.execute("""
                    INSERT INTO payment_transactions (id, payment_request_id, wallet_id, event_id, amount, currency, transaction_type, status, idempotency_key)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::payment_transaction_type, %s::payment_transaction_status, %s)
                    RETURNING id, status, created_at
                """, (str(uuid.uuid4()), payment_request_id, wallet_id, event_id, refund_amount, currency, 'SETTLEMENT', 'REFUNDED', idempotency_key))
                refund_row = cur.fetchone()

                conn.commit()
                return {
                    "refund_transaction_id": refund_row[0],
                    "original_settled_id": settled_id,
                    "status": refund_row[1],
                    "message": "Payment refunded successfully."
                }
        except Exception as e:
            conn.rollback()
            raise
        finally:
            self.db_pool.put_connection(conn)
