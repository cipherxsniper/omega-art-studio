import json
import omega_event_bus_core_v1 as event_bus


def apply_settlement(_events=None):
    events = event_bus.get_recent_events()

    balances = {
        "OMEGA_TREASURY": 0.0,
        "OMEGA_CREDIT": 0.0,
        "OMEGA_RESERVE": 0.0,
        "OMEGA_INVESTMENT": 0.0,
        "THOMAS_LH": 0.0
    }

    for e in events:
        try:
            payload = e.get("payload_json")

            # 🔥 CRITICAL FIX: deserialize string → dict
            if isinstance(payload, str):
                payload = json.loads(payload)

            effect = payload.get("ledger_effect", {})

            for k, v in effect.items():
                balances[k] = balances.get(k, 0.0) + float(v)

        except Exception:
            continue

    return {
        "settled_balances": balances,
        "event_count": len(events),
        "status": "SETTLED"
    }
