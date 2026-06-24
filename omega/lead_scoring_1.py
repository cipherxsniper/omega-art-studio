def score_lead(lead):
    score = 0

    if lead.get("email"):
        score += 20

    if lead.get("company"):
        score += 30

    if lead.get("source") in ["google", "business_listing"]:
        score += 40

    return min(score, 100)
