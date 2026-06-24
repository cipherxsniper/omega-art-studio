def generate_pitch(lead, plan="growth"):
    name = lead.get("name", "there")
    company = lead.get("company", "your business")

    return f"""
Hey {name},

I built a system that automates outreach, lead tracking, and revenue generation for businesses like {company}.

Most companies waste time manually doing sales + follow-up.

This system replaces that with automated revenue operations.

Plan: {plan}
Includes automation + CRM + outreach + revenue tracking.

If you want, I can activate it instantly via Stripe checkout.
"""
