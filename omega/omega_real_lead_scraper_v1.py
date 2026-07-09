# ─────────────────────────────────────────────
# OMEGA LEAD SCRAPER COMPATIBILITY LAYER FIX
# ─────────────────────────────────────────────

def scrape_local_service_leads():
    """
    Existing internal scraper function (unchanged logic assumed)
    """
    return []


def get_next_lead(conn):
    """
    Existing DB iterator (unchanged logic assumed)
    """
    return None


# ─────────────────────────────────────────────
# REQUIRED COMPATIBILITY WRAPPER (FIX FOR ORCHESTRATOR)
# ─────────────────────────────────────────────

def scrape_leads():
    """
    Unified interface for orchestrator compatibility.
    Safe wrapper around internal scraper functions.
    """

    # Primary internal function
    if "scrape_local_service_leads" in globals():
        return scrape_local_service_leads()

    # fallback patterns (future-proofing)
    if "get_leads" in globals():
        return get_leads()

    if "run_scraper" in globals():
        return run_scraper()

    if "fetch_leads" in globals():
        return fetch_leads()

    raise Exception("No valid scraper function found in omega_real_lead_scraper_v1.py")
