def normalize_event(row):
    return {
        "event_id": row.get("event_id") or row.get("tx_id") or row.get("id"),
        "from_account": row.get("from_account") or row.get("from"),
        "to_account": row.get("to_account") or row.get("to"),
        "amount": Decimal(str(row.get("amount", "0"))),
        "currency": row.get("currency", "USD"),
        "timestamp": row.get("timestamp") or row.get("created_at"),
    }
