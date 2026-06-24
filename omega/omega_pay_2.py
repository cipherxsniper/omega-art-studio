
import uuid
from decimal import Decimal
import logging

from config import DatabasePool
from events import EventStore
from wallets import WalletManager
from credit import CreditIssuer
from risk_engine import RiskEngine
from card_issuer import CardIssuer
from tokenization import TokenizationEngine
from merchant import MerchantSystem
from authorization_engine import AuthorizationEngine
from settlement import SettlementEngine
from payment_channels import PaymentChannels
from treasury import TreasuryCoordinator

# Configure logging for the Omega Pay system
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/home/ubuntu/omega_pay_system/omega_pay.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OmegaPaySystem:
    def __init__(self):
        self.db_pool = DatabasePool.get_pool()
        self.event_store = EventStore(self.db_pool)
        self.wallet_manager = WalletManager(self.db_pool, self.event_store)
        self.credit_issuer = CreditIssuer(self.db_pool, self.event_store)
        self.risk_engine = RiskEngine(self.db_pool, self.event_store, self.credit_issuer, self.treasury_coordinator)
        self.card_issuer = CardIssuer(self.db_pool, self.event_store)
        self.tokenization_engine = TokenizationEngine(self.db_pool, self.event_store)
        self.merchant_system = MerchantSystem(self.db_pool, self.event_store)
        self.treasury_coordinator = TreasuryCoordinator(self.db_pool, self.event_store)

        self.authorization_engine = AuthorizationEngine(
            self.db_pool, self.event_store, self.wallet_manager, self.credit_issuer, self.risk_engine
        )
        self.settlement_engine = SettlementEngine(
            self.db_pool, self.event_store, self.credit_issuer, self.treasury_coordinator
        )
        self.payment_channels = PaymentChannels()
        logger.info("OmegaPaySystem initialized successfully.")

    def create_new_wallet_and_card(self, user_id: str, initial_credit_limit: Decimal = Decimal("1000.00")) -> Dict[str, Any]:
        """Creates a new wallet, assigns a credit line, and issues a card."""
        logger.info(f"Creating new wallet and card for user_id: {user_id}")
        wallet = self.wallet_manager.create_wallet(user_id)
        self.credit_issuer.assign_credit_line(wallet["id"], initial_credit_limit)
        card = self.card_issuer.issue_card(wallet["id"])
        logger.info(f"Wallet {wallet["id"]} and Card {card["id"]} created for user {user_id}")
        return {"wallet": wallet, "card": card}

    def process_payment_request(self, payment_request_id: str, wallet_id: str, card_or_token_id: str, amount: Decimal, currency: str, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        """Processes a payment request through authorization and settlement."""
        logger.info(f"Processing payment request {payment_request_id} for wallet {wallet_id} with amount {amount} {currency}")
        
        # Determine if card_or_token_id is a card or token
        card_id = None
        token_id = None
        if len(card_or_token_id) == 36: # Assuming UUID for card/token IDs
            # Try to get card first
            card_info = self.card_issuer.get_card(card_or_token_id)
            if card_info:
                card_id = card_info["id"]
            else:
                token_info = self.tokenization_engine.get_token(card_or_token_id)
                if token_info:
                    token_id = token_info["id"]
                    card_id = token_info["card_id"]
                else:
                    raise ValueError("Invalid card or token ID provided.")
        else:
            # Assume it's a card number for now, though in a real system this would be more robust
            card_info = self.card_issuer.get_card_by_number(card_or_token_id)
            if card_info:
                card_id = card_info["id"]
            else:
                raise ValueError("Invalid card number or token value provided.")

        # 1. Authorize payment
        auth_result = self.authorization_engine.authorize_payment(
            payment_request_id, wallet_id, card_id, token_id, amount, currency, idempotency_key
        )
        logger.info(f"Payment request {payment_request_id} authorized: {auth_result["status"]}")

        # 2. Settle payment
        settlement_result = self.settlement_engine.settle_payment(auth_result["transaction_id"], idempotency_key=idempotency_key)
        logger.info(f"Payment request {payment_request_id} settled: {settlement_result["status"]}")

        return {"authorization": auth_result, "settlement": settlement_result}

    def close(self):
        """Closes the database connection pool."""
        DatabasePool.close_all()
        logger.info("OmegaPaySystem shut down. Database pool closed.")

