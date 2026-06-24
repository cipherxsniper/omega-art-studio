"""
OMEGA STRIPE TEST RUNNER
Uses ONLY Stripe TEST LINKS
Triggers checkout.session.completed safely
"""

import webbrowser
import time

TEST_LINK = "https://buy.stripe.com/test_fZu00i8YLgbP2kXckoa7C00"

def run_test():
    print("[STRIPE TEST] Opening checkout session (TEST MODE ONLY)")
    webbrowser.open(TEST_LINK)

    print("[WAIT] Complete checkout manually in browser")
    time.sleep(3)

    print("[INFO] Webhook should fire automatically if tunnel is active")
    print("[NEXT] Run: python omega_runtime_probe.py")


if __name__ == "__main__":
    run_test()
