#!/usr/bin/env python3
"""
OMEGA OUTREACH ENGINE
Sends professional outreach emails with Stripe payment links.
When client pays -> webhook fires -> auto onboarding begins.
"""
import re, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

HOME = Path("/data/data/com.termux/files/home")

def env(key):
    for line in (HOME / ".env").read_text().splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip()
    return ""

SMTP_USER     = env("SMTP_USER")
SMTP_PASS     = env("SMTP_PASS")
COMPANY_NAME  = env("COMPANY_NAME")
CEO_NAME      = env("CEO_NAME")
STARTER_LINK  = "https://buy.stripe.com/fZu00i8YLgbP2kXckoa7C00"
GROWTH_LINK   = "https://buy.stripe.com/dRm6oGfn9aRvcZBgAEa7C01"
FULL_LINK     = "https://buy.stripe.com/bJe5kCcaX4t72kX0BGa7C02"

def domain_to_name(domain):
    name = domain.split(".")[0]
    name = re.sub(r"[-_]", " ", name)
    return name.title()

def send_outreach(to_email, domain, city):
    biz_name = domain_to_name(domain)
    subject  = f"Automate {biz_name}'s operations — 3 options"
    body = f"""Hi {biz_name} team,

I wanted to reach out about automating your business operations.

At {COMPANY_NAME}, we help businesses like yours in {city.title()} run on autopilot — client onboarding, payments, follow-ups, and reporting handled automatically.

We have three simple plans:

🚀 Starter — Core automation
{STARTER_LINK}

📈 Growth — Full business automation  
{GROWTH_LINK}

⚡ Full Ops — Enterprise-level system
{FULL_LINK}

Pick a plan, complete checkout, and your system will be live within 60 seconds. No calls needed.

Best,
{CEO_NAME}
{COMPANY_NAME}
omegaops.ai@gmail.com
"""
    try:
        msg = MIMEMultipart()
        msg["From"]    = SMTP_USER
        msg["To"]      = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as s:
            s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(SMTP_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"  [SMTP ERROR] {e}")
        return False

if __name__ == "__main__":
    # Test
    print(domain_to_name("carmelatl.com"))
    print(domain_to_name("five-star-plumbing.com"))
