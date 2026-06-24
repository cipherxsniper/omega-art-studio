from database.leads_db import leads_db
from core.pitch_engine import generate_pitch
from integrations.funnel_checkout import generate_checkout


def fetch_scored():
    import sqlite3
    conn = sqlite3.connect("leads.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM leads WHERE status='scored' AND score > 60")
    return cur.fetchall()


def update_status(lead_id, status):
    import sqlite3
    conn = sqlite3.connect("leads.db")
    conn.execute("UPDATE leads SET status=? WHERE id=?", (status, lead_id))
    conn.commit()


while True:
    leads = fetch_scored()

    for lead in leads:
        lead_id, name, email, company, source, score, status, created = lead

        lead_obj = {
            "name": name,
            "email": email,
            "company": company
        }

        pitch = generate_pitch(lead_obj)

        checkout_url = generate_checkout(email, plan="growth")

        print("\n--- PITCH ---")
        print(pitch)
        print("\n--- CHECKOUT ---")
        print(checkout_url)

        update_status(lead_id, "sent")

        print(f"[SALES] Sent offer to {email}")
