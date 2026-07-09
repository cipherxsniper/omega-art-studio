#!/usr/bin/env python3
"""
Send fresh Stripe checkout links to Victoria and Trevor.
Standalone — uses same SMTP config as omega_v10.py EmailEngine.
"""
import os, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from dotenv import load_dotenv

HOME = Path.home()
load_dotenv(HOME / ".env")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
CEO_NAME  = os.getenv("CEO_NAME", "Thomas Lee Harvey")
COMPANY_NAME = os.getenv("COMPANY_NAME", "Omega AI")

def send(to_email, subject, body):
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{CEO_NAME} | {COMPANY_NAME} <{SMTP_USER}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
        s.ehlo(); s.starttls(); s.ehlo()
        s.login(SMTP_USER, SMTP_PASS)
        s.sendmail(SMTP_USER, to_email, msg.as_string())
    print(f"Sent to {to_email}")

CLIENTS = [
    {
        "email": "bbygirlv94@gmail.com",
        "name": "Victoria",
        "url": "https://checkout.stripe.com/c/pay/cs_live_a11COnaCEvHaVI810jthhZjxR5NDZ97ZVlTnxgWmJKB7upgZ5xRy0DAai0#fidnandhYHdWcXxpYCc%2FJ2FgY2RwaXEnKSd2cGd2ZndsdXFsamtQa2x0cGBrYHZ2QGtkZ2lgYSc%2FY2RpdmApJ2JwZGZkaGppYFNkd2xka3EnPydmamtxd2ppJyknZHVsTmB8Jz8ndW5aaWxzYFowNFFdXFcyRDB9dlcxaXNIMUJPMFxqMWxEMTRuYUZGUEk9VGtHSHFPXzN9Nm9pc1RXZ3BVM3Z2bH00UFZ8c3BPSXIwZ3NObTMwY3E1ZjZMTlZsYVJJTGthfDU1VGs8Q0Z2ZEEnKSdjd2poVmB3c2B3Jz9xd3BgKSdnZGZuYndqcGthRmppancnPycmNTVjY2NjJyknaWR8anBxUXx1YCc%2FJ3Zsa2JpYFpscWBoJyknYGtkZ2lgVWlkZmBtamlhYHd2Jz9xd3BgeCUl",
    },
    {
        "email": "theenjoupanda23@gmail.com",
        "name": "Trevor",
        "url": "https://checkout.stripe.com/c/pay/cs_live_a1YcoEfLvYEOSplrVOKusAB0boosxpxpDcBVjIh8rIla83ZlFsQnXQHKiB#fidnandhYHdWcXxpYCc%2FJ2FgY2RwaXEnKSd2cGd2ZndsdXFsamtQa2x0cGBrYHZ2QGtkZ2lgYSc%2FY2RpdmApJ2JwZGZkaGppYFNkd2xka3EnPydmamtxd2ppJyknZHVsTmB8Jz8ndW5aaWxzYFowNFFdXFcyRDB9dlcxaXNIMUJPMFxqMWxEMTRuYUZGUEk9VGtHSHFPXzN9Nm9pc1RXZ3BVM3Z2bH00UFZ8c3BPSXIwZ3NObTMwY3E1ZjZMTlZsYVJJTGthfDU1VGs8Q0Z2ZEEnKSdjd2poVmB3c2B3Jz9xd3BgKSdnZGZuYndqcGthRmppancnPycmNTVjY2NjJyknaWR8anBxUXx1YCc%2FJ3Zsa2JpYFpscWBoJyknYGtkZ2lgVWlkZmBtamlhYHd2Jz9xd3BgeCUl",
    },
]

for c in CLIENTS:
    subject = "Complete Your Omega AI Full Ops Activation"
    body = f"""Hi {c['name']},

Thanks for your interest in Omega AI Full Ops.

To activate your account and get started, please complete your subscription here:

{c['url']}

This link is valid for 24 hours. Once completed, I'll reach out personally to begin onboarding.

Best,
{CEO_NAME}
{COMPANY_NAME}
"""
    send(c["email"], subject, body)
