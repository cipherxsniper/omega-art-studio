#!/usr/bin/env python3

import os
import json
import uuid
import logging
from datetime import datetime, UTC

import omega_event_bus_core_v1 as event_bus
import omega_settlement_engine_v1 as settlement
import omega_stripe_binding_layer_v1 as stripe

LEADS_PATH = "omega_leads.json"
CRM_PATH = "omega_crm.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OMEGA_REVENUE")

def now():
    return datetime.now(UTC).isoformat()

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def ingest_lead(business_name, email, niche):

    leads = load_json(LEADS_PATH)

    lead = {
        "lead_id": str(uuid.uuid4()),
        "business_name": business_name,
        "email": email,
        "niche": niche,
        "status": "NEW",
        "created_at": now()
    }

    leads.append(lead)

    save_json(LEADS_PATH, leads)

    logger.info(f"Lead ingested: {business_name}")

    return lead

def queue_outreach(lead):

    crm = load_json(CRM_PATH)

    record = {
        "crm_id": str(uuid.uuid4()),
        "lead_id": lead["lead_id"],
        "business_name": lead["business_name"],
        "status": "OUTREACH_QUEUED",
        "queued_at": now()
    }

    crm.append(record)

    save_json(CRM_PATH, crm)

    return record

def emit_revenue_event(client_name, amount):

    event = {
        "event_type": "STRIPE_PAYMENT",
        "currency": "USD",
        "ledger_effect": {
            "OMEGA_TREASURY": amount,
            "REVENUE": -amount
        },
        "client_name": client_name,
        "timestamp": now()
    }

    conn = event_bus.connect_db()
    cur = conn.cursor()

    event_bus.ensure_schema(cur)
    result = event_bus.insert_event(cur, event)

    conn.commit()
    conn.close()

    return result

def run_demo():

    lead = ingest_lead(
        "Acme Roofing",
        "owner@acmeroofing.com",
        "roofing"
    )

    queue = queue_outreach(lead)

    revenue = emit_revenue_event(
        "Acme Roofing",
        1497.00
    )

    settlement_events = [(str(i), e.get("event_type","UNKNOWN"), e, e.get("timestamp","")) for i, e in enumerate(event_bus.get_recent_events())]
    snapshot = settlement.apply_settlement(settlement_events)

    print(json.dumps({
        "lead": lead,
        "queue": queue,
        "revenue_event": revenue,
        "settlement_snapshot": snapshot
    }, indent=2))

if __name__ == "__main__":
    run_demo()

