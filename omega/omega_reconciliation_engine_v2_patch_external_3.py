from omega_reconciliation_bridge_patch_v1 import fetch_external_webhook_events

def reconcile_with_external_check(base_results):
    external_events = fetch_external_webhook_events()

    external_map = {e["id"]: e for e in external_events}

    enriched = []

    for item in base_results:
        item["external_state"] = external_map.get(item["id"], None)
        item["external_status"] = "FOUND" if item["id"] in external_map else "MISSING_EXTERNAL"
        enriched.append(item)

    return enriched
