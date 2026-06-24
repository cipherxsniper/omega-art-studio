#!/usr/bin/env python3

import json

def classify_reply(email_text):
    """
    SIMPLE REPLY INTELLIGENCE LAYER
    """

    text = email_text.lower()

    if "not interested" in text:
        return "DISQUALIFIED"

    if "yes" in text or "demo" in text:
        return "INTERESTED"

    if "pricing" in text:
        return "HIGH_INTENT"

    if "stop" in text or "unsubscribe" in text:
        return "OPT_OUT"

    return "FOLLOW_UP"


def generate_next_action(classification):
    """
    Maps intent → CRM action
    """

    mapping = {
        "DISQUALIFIED": "MARK_LOST",
        "INTERESTED": "SCHEDULE_DEMO",
        "HIGH_INTENT": "PRIORITY_FOLLOWUP",
        "OPT_OUT": "REMOVE",
        "FOLLOW_UP": "SEND_FOLLOWUP"
    }

    return mapping.get(classification, "SEND_FOLLOWUP")


if __name__ == "__main__":
    print("[REPLY INTELLIGENCE] READY")
