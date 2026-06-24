#!/usr/bin/env python3

import time
from omega_acquisition_engine_v1 import get_next_lead
from omega_sendgrid_adapter_v1 import send_email
from omega_crm_state_machine_v1 import update_lead_state

SENDER = "omegaops.ai@gmail.com"

def run_outbound_cycle(conn):
    """
    LIVE OUTBOUND ENGINE
    - pulls leads
    - sends email
    - updates CRM state
    """

    lead = get_next_lead(conn)

    if not lead:
        print("[OUTBOUND] No leads available")
        return

    email = lead["email"]

    subject = "Increase bookings automatically"
    body = f"""
Hi {lead.get('name', 'there')},

We help local service businesses automate lead generation, follow-ups, and booking.

Would you be open to a 10-minute demo?

- Omega AI
"""

    print(f"[OUTBOUND] Sending -> {email}")

    result = send_email(
        sender=SENDER,
        recipient=email,
        subject=subject,
        body=body
    )

    update_lead_state(conn, email, "EMAIL_SENT")

    return {
        "lead": email,
        "status": "sent",
        "provider_response": result
    }

if __name__ == "__main__":
    print("[OUTBOUND ENGINE] ACTIVE")
