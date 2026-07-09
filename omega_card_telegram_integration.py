#!/usr/bin/env python3
"""
Quick helper to wire sovereign card issuance into Telegram
"""

import sys
sys.path.insert(0, "/data/data/com.termux/files/home")
from omega_tokenization_engine import issue_and_tokenize

if __name__ == "__main__":
    print("=== TELEGRAM CARD ISSUANCE READY ===")
    card = issue_and_tokenize()
    print("\nCopy this into your Telegram card handler:")
    print(f"card_token = \"{card['card']['card_token']}\"")
