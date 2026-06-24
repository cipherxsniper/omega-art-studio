price_id = (
    session.get("metadata", {}).get("price_id")
    or session.get("subscription_details", {}).get("price", {}).get("id")
)
