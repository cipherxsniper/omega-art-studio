#!/usr/bin/env python3

import os
import requests

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")

SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"


def send_email(sender, recipient, subject, body):
    """
    REAL EMAIL SENDING LAYER (SendGrid)
    """

    if not SENDGRID_API_KEY:
        print("[ERROR] Missing SendGrid API key")
        return {"status": "failed", "reason": "no_api_key"}

    payload = {
        "personalizations": [{
            "to": [{"email": recipient}],
            "subject": subject
        }],
        "from": {"email": sender},
        "content": [{
            "type": "text/plain",
            "value": body
        }]
    }

    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        SENDGRID_URL,
        json=payload,
        headers=headers
    )

    return {
        "status_code": response.status_code,
        "response": response.text
    }


if __name__ == "__main__":
    print(send_email(
        "omegaops.ai@gmail.com",
        "test@example.com",
        "Test",
        "Hello from Omega"
    ))
