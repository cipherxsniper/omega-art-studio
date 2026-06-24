#!/usr/bin/env python3
"""
OMEGA BANK COMMAND (CLI ENTRYPOINT)
Run: bank
"""

import subprocess
import sys
import os


def main():
    path = os.path.join(os.path.dirname(__file__), "event_ledger_engine.py")

    print("\n🏦 OMEGA BANK INITIALIZING...\n")
    subprocess.run(["python", path])


if __name__ == "__main__":
    main()
