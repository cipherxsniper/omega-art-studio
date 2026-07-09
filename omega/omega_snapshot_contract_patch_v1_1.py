def normalize_snapshot(snapshot: dict):
    """
    Enforces canonical snapshot schema.
    Fixes legacy key drift between modules.
    """

    snapshot = dict(snapshot or {})

    # FIX KEY DRIFT
    if "ledger_event_count" not in snapshot:
        snapshot["ledger_event_count"] = snapshot.get("event_count", 0)

    if "event_count" not in snapshot:
        snapshot["event_count"] = snapshot.get("ledger_event_count", 0)

    return snapshot
