from typing import Dict, List

# =========================================================
# OMEGA FINANCIAL KERNEL v1
# Deterministic Event → Ledger Contract Engine
# =========================================================

class FinancialKernelV1:

    # 🔒 ONLY EVENTS ALLOWED INTO LEDGER DOMAIN
    FINANCIAL_EVENTS = {
        "PAYMENT_CAPTURED",
        "PAYMENT_SETTLED",
        "PAYMENT_RESERVED"
    }

    # 🔒 STRICT POSTING CONTRACT (NO IMPROVISATION)
    EVENT_TO_POSTINGS: Dict[str, List[Dict]] = {
        "PAYMENT_CAPTURED": [
            {"account_type": "wallet", "direction": "DEBIT"},
            {"account_type": "merchant", "direction": "CREDIT"},
            {"account_type": "treasury", "direction": "DEBIT"}
        ],

        "PAYMENT_SETTLED": [
            {"account_type": "merchant", "direction": "DEBIT"},
            {"account_type": "treasury", "direction": "CREDIT"}
        ],

        "PAYMENT_RESERVED": [
            {"account_type": "wallet", "direction": "DEBIT"},
            {"account_type": "treasury", "direction": "CREDIT"}
        ]
    }

    @staticmethod
    def is_financial_event(event_type: str) -> bool:
        return event_type in FinancialKernelV1.FINANCIAL_EVENTS

    @staticmethod
    def get_posting_contract(event_type: str):
        if event_type not in FinancialKernelV1.EVENT_TO_POSTINGS:
            return None
        return FinancialKernelV1.EVENT_TO_POSTINGS[event_type]
