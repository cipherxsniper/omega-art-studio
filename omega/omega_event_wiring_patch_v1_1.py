# =========================================================
# OMEGA FULL EVENT WIRING PATCH v1
# CFO REAL-TIME FINANCIAL OS INTEGRATION LAYER
# =========================================================

import uuid
from datetime import datetime

# Assumes event_bus is already imported in runtime modules

# ---------------------------------------------------------
# SAFE EVENT EMITTER (UNIVERSAL)
# ---------------------------------------------------------

def emit_event(event_type, payload):
    try:
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload
        }

        # PRIMARY LEDGER WRITE
        if hasattr(event_bus, "insert_event"):
            return event_bus.insert_event(event)

        # FALLBACK WRITE METHOD
        if hasattr(event_bus, "write_event"):
            return event_bus.write_event(event)

        raise Exception("No valid event write method found")

    except Exception as e:
        print(f"[EVENT_EMIT_ERROR] {e}")
        return None


# ---------------------------------------------------------
# WALLET EVENT WIRING
# ---------------------------------------------------------

def wire_wallet_created(wallet):
    return emit_event("WALLET_CREATED", wallet)


def wire_wallet_balance_update(wallet_id, balance):
    return emit_event("WALLET_BALANCE_UPDATE", {
        "wallet_id": wallet_id,
        "balance": balance
    })


# ---------------------------------------------------------
# TRANSFER EVENT WIRING
# ---------------------------------------------------------

def wire_transfer_intent(sender, receiver, amount):
    return emit_event("TRANSFER_INTENT", {
        "from": sender,
        "to": receiver,
        "amount": amount
    })


# ---------------------------------------------------------
# CARD EVENT WIRING
# ---------------------------------------------------------

def wire_card_issued(card):
    return emit_event("CARD_ISSUED", card)


# ---------------------------------------------------------
# SETTLEMENT EVENT WIRING
# ---------------------------------------------------------

def wire_settlement_event(snapshot):
    return emit_event("SETTLEMENT_EVENT", snapshot)


# ---------------------------------------------------------
# QR EVENT WIRING
# ---------------------------------------------------------

def wire_qr_intent(qr_data):
    return emit_event("QR_PAYMENT_INTENT", qr_data)


# ---------------------------------------------------------
# OPTIONAL HOOK PATCH HELPERS
# ---------------------------------------------------------

def safe_emit(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        print(f"[SAFE_EMIT_ERROR] {e}")
        return None


# =========================================================
# SYSTEM INTENT:
# ALL MODULES SHOULD NOW CALL THESE WRAPPERS ONLY
# NOT DIRECT EVENT BUS ACCESS FROM BUSINESS LOGIC
# =========================================================
