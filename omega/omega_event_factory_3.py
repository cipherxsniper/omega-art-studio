import uuid


def normalize_stripe_event(event):

    # ---------------------------------
    # STRIPE OBJECT -> DICT
    # ---------------------------------
    if hasattr(event, "to_dict"):
        event = event.to_dict()

    data_object = (
        event.get("data", {})
             .get("object", {})
    )

    metadata = data_object.get("metadata", {})

    amount = float(data_object.get("amount", 0)) / 100.0

    currency = str(
        data_object.get("currency", "usd")
    ).upper()

    wallet_id = metadata.get(
        "wallet_id",
        "00000000-0000-0000-0000-000000000000"
    )

    merchant_id = metadata.get(
        "merchant_id",
        "11111111-1111-1111-1111-111111111111"
    )

    stripe_payment_intent = data_object.get(
        "id",
        "UNKNOWN_STRIPE_ID"
    )

    internal_event_id = str(uuid.uuid4())

    # ---------------------------------
    # CANONICAL OMEGA EVENT
    # ---------------------------------
    omega_event = {
        "event_id": internal_event_id,

        # REQUIRED BY EVENT STORE
        "aggregate_id": wallet_id,

        "event_type": "PAYMENT_CAPTURED",

        "external_id": stripe_payment_intent,

        "source": "STRIPE",

        "payload": {
            "wallet_id": wallet_id,
            "merchant_id": merchant_id,
            "amount": str(amount),
            "currency": currency
        }
    }

    return omega_event


if __name__ == "__main__":
    print("✅ omega_event_factory loaded")
