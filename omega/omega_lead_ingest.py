# AUTO-GENERATED MODULE (Omega System Bootstrap)

try:
    from omega_lead_scraper import run_scraper
except Exception:
    run_scraper = None

from omega_event_queue import enqueue

def ingest_leads_to_queue():
    if run_scraper is None:
        return 0

    leads = run_scraper()
    count = 0

    for lead in leads:
        try:
            enqueue(
                "LEAD_DISCOVERED",
                lead.get("industry", "unknown"),
                lead.get("business_name", "unknown"),
                {
                    "business_name": lead.get("business_name"),
                    "website": lead.get("website"),
                    "industry": lead.get("industry"),
                    "score": lead.get("score", 0),
                    "intent": lead.get("intent", "cold_discovery")
                }
            )
            count += 1
        except Exception:
            continue

    return count
