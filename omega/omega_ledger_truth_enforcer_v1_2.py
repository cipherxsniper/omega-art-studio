def enforce_single_source_of_truth():

    return {
        "rule": "ledger_events_only",
        "status": "ENFORCED",
        "disabled_sources": [
            "accounts.balance",
            "subscriptions.state",
            "cache_balances"
        ]
    }
