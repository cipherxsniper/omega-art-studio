#!/usr/bin/env python3

import uuid
from datetime import datetime, UTC

from omega_revenue_pipeline_v1 import run_demo as run_pipeline
from omega_cfo_net_worth_engine_v1 import run_net_worth_engine
from omega_event_bus_core_v1 import insert_event, connect_db


REVENUE_EVENT_TYPE = "REVENUE_INTAKE"


def utc_now():
    return datetime.now(UTC).isoformat()


def build_revenue_event(lead):
    return {
        "event_type": "STRIPE_PAYMENT",
        "currency": "USD",
        "ledger_effect": {
            "OMEGA_TREASURY": float(lead.get("expected_value", 0)),
            "REVENUE": -float(lead.get("expected_value", 0))
        },
        "lead_id": lead.get("lead_id"),
        "source": "REVENUE_INTAKE_LOOP",
        "timestamp": utc_now()
    }


def process_lead(lead):
    conn = connect_db()
    cur = conn.cursor()

    event = build_revenue_event(lead)

    result = insert_event(event)

    conn.commit()
    conn.close()

    return {
        "lead": lead,
        "event": result,
        "status": "REVENUE_INTAKE_PROCESSED"
    }


def run_revenue_intake_loop():
    leads = [
        {
            "lead_id": str(uuid.uuid4()),
            "business_name": "Acme Roofing",
            "email": "owner@acmeroofing.com",
            "expected_value": 1497.00
        },
        {
            "lead_id": str(uuid.uuid4()),
            "business_name": "HVAC Pro Services",
            "email": "owner@hvacpro.com",
            "expected_value": 2997.00
        }
    ]

    results = []

    for lead in leads:
        results.append(process_lead(lead))

    net_worth = run_net_worth_engine()

    return {
        "status": "REVENUE_LOOP_ACTIVE",
        "processed": len(results),
        "results": results,
        "net_worth": net_worth
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_revenue_intake_loop(), indent=2))
