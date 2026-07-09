# safer column mapping (tuple-safe fallback)
for sub in rows:

    # tuple fallback mapping based on schema:
    # (id, subscription_id, customer_id, status, price_id, ...)
    try:
        subscription_id = sub[1] if len(sub) > 1 else "NULL_SUB"
        customer_id = sub[2] if len(sub) > 2 else sub[0]
        price_id = sub[4] if len(sub) > 4 else "UNKNOWN_PRICE"
    except Exception:
        continue

    tx_id = make_tx_id(customer_id, subscription_id, price_id)

    if already_exists(ledger, tx_id):
        skipped += 1
        continue
