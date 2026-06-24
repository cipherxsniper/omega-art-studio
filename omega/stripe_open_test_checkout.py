import omega_sqlite_override
#!/usr/bin/env python3

import os
import webbrowser
import time

TEST_CHECKOUT_URL = "https://buy.stripe.com/test_fZu00i8YLgbP2kXckoa7C00"

def open_checkout():
    print("\n=== STRIPE TEST CHECKOUT ===")
    print("URL:", TEST_CHECKOUT_URL)

    try:
        # Try system browser
        webbrowser.open(TEST_CHECKOUT_URL)
        print("[OK] Browser open attempted")
    except Exception as e:
        print("[WARN] Auto-open failed:", str(e))
        print("[ACTION] Manually open URL above")

    time.sleep(1)

if __name__ == "__main__":
    open_checkout()
