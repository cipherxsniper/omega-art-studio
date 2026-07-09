import os
import json
import time
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

LEADS_FILE = "leads/leads.json"
LOG_FILE = "logs/sent.log"
CONFIG_FILE = "config.json"

# =========================
# LOAD CONFIG
# =========================
def load_config():
    return json.load(open(CONFIG_FILE))

# =========================
# LOAD LEADS
# =========================
def load_leads():
    if not os.path.exists(LEADS_FILE):
        return []
    return json.load(open(LEADS_FILE))

# =========================
# LOGGING
# =========================
def log_sent(to_email, subject):
    os.makedirs("logs", exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.utcnow()} | {to_email} | {subject}\n")

# =========================
# BUILD EMAIL
# =========================
def build_message(name):
    return f"""Hi {name},

Quick question — are you currently looking to get more customers?

We help local businesses book qualified appointments automatically using AI-driven outreach.

If you're open, I can show you how it works.

- Omega AI
"""

# =========================
# SEND EMAIL (REAL SMTP)
# =========================
def send_email(to_email, name, config):
    msg = MIMEText(build_message(name))
    msg["Subject"] = "Quick question about your business"
    msg["From"] = config["gmail_user"]
    msg["To"] = to_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(config["gmail_user"], config["gmail_app_password"])
        server.sendmail(config["gmail_user"], to_email, msg.as_string())
        server.quit()

        print(f"[SENT] {to_email}")
        log_sent(to_email, msg["Subject"])

    except Exception as e:
        print(f"[FAILED] {to_email} -> {e}")

# =========================
# RUN LOOP
# =========================
def run():
    config = load_config()
    leads = load_leads()

    print(f"[LOADED] {len(leads)} leads")

    for lead in leads:
        send_email(lead["contact"], lead["name"], config)
        time.sleep(3)  # rate limit safety

    print("[DONE] real outbound cycle complete")

if __name__ == "__main__":
    run()
