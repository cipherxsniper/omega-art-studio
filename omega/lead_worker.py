import sqlite3
from database.leads_db import leads_db
from core.lead_scoring import score_lead

DB = "leads.db"


def fetch_leads():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT * FROM leads WHERE status='new'")
    return cur.fetchall()


def update_score(lead_id, score):
    conn = sqlite3.connect(DB)
    conn.execute("UPDATE leads SET score=?, status='scored' WHERE id=?", (score, lead_id))
    conn.commit()


while True:
    leads = fetch_leads()

    for lead in leads:
        lead_id, name, email, company, source, score, status, created = lead

        lead_obj = {
            "name": name,
            "email": email,
            "company": company,
            "source": source
        }

        new_score = score_lead(lead_obj)

        update_score(lead_id, new_score)

        print(f"[LEAD] {name} scored {new_score}")
