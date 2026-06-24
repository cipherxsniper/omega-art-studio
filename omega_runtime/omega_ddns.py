#!/usr/bin/env python3
import urllib.request
import logging
import os

TOKEN  = "a39028c0-d067-493f-a782-217b92d3b0d8"
DOMAIN = "omega-node3"
LOG    = os.path.expanduser("~/omega_runtime/logs/ddns.log")

logging.basicConfig(
    filename=LOG,
    level=logging.INFO,
    format="[%(asctime)s] %(message)s"
)

def update():
    url = f"https://www.duckdns.org/update?domains={DOMAIN}&token={TOKEN}&ip="
    try:
        res = urllib.request.urlopen(url, timeout=10).read().decode()
        if res.strip() == "OK":
            logging.info("DDNS updated successfully")
            print("✅ DDNS OK")
        else:
            logging.warning(f"DDNS unexpected response: {res}")
            print(f"⚠️  DDNS response: {res}")
    except Exception as e:
        logging.error(f"DDNS update failed: {e}")
        print(f"❌ DDNS failed: {e}")

if __name__ == "__main__":
    update()
