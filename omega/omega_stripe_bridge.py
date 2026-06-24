#!/usr/bin/env python3
"""
omega_stripe_bridge.py — Stripe Issuing + Treasury Bridge
Connects Stripe Issuing API to omega_bank treasury wallet.
Pure Python, urllib only, no SDK.

Commands:
  python3 omega_stripe_bridge.py balance       # Stripe balance
  python3 omega_stripe_bridge.py create_card   # Issue new virtual card
  python3 omega_stripe_bridge.py list_cards    # All issued cards
  python3 omega_stripe_bridge.py card <id>     # Single card details
  python3 omega_stripe_bridge.py reconcile     # Sync Stripe spend to ledger
  python3 omega_stripe_bridge.py webhook       # Start webhook listener
"""

import os, sys, json, uuid, hashlib, hmac
import urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
HOME             = Path("/data/data/com.termux/files/home")
load_dotenv(HOME / ".env")
STRIPE_SECRET    = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK   = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_API       = "https://api.stripe.com/v1"

# Treasury wallet — matches omega_bank
TREASURY_WALLET  = "80795b24-da42-4b9f-aa32-0349004880dc"
CARD_FLOAT_ACCT  = "omega_card_float"

# Postgres connection for omega_bank ledger
PG_HOST          = "127.0.0.1"
PG_PORT          = 5432
PG_DB            = "omega_bank"
PG_USER          = "postgres"

WEBHOOK_PORT     = int(os.getenv("STRIPE_WEBHOOK_PORT", 5010))

# ---------------------------------------------------------------------------
# Stripe API caller — raw urllib, no SDK
# ---------------------------------------------------------------------------
def stripe_request(method: str, endpoint: str,
                   data: dict = None) -> dict:
    if not STRIPE_SECRET:
        raise ValueError("STRIPE_SECRET_KEY not set in environment")

    url     = f"{STRIPE_API}/{endpoint}"
    payload = urllib.parse.urlencode(data).encode() if data else None

    req = urllib.request.Request(
        url, data=payload, method=method.upper(),
        headers={
            "Authorization": f"Bearer {STRIPE_SECRET}",
            "Content-Type":  "application/x-www-form-urlencoded",
            "Stripe-Version": "2023-10-16",
        }
    )
    try:
        res  = urllib.request.urlopen(req, timeout=30)
        return json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"Stripe HTTP {e.code}: {body}")

# ---------------------------------------------------------------------------
# Ledger integration — double-entry into omega_bank
# ---------------------------------------------------------------------------
def post_ledger_entry(description: str, amount_cents: int,
                      direction: str, reference: str,
                      idempotency_key: str):
    """
    Post a double-entry ledger record to omega_bank.
    direction: 'DEBIT' or 'CREDIT' relative to treasury.
    amount_cents: amount in cents (Stripe native unit).
    """
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT,
            dbname=PG_DB, user=PG_USER,
            connect_timeout=5
        )
        cur  = conn.cursor()
        amount_dollars = amount_cents / 100.0
        tx_id          = str(uuid.uuid4())

        # Double-entry: treasury ↔ card_float
        if direction == "DEBIT":
            debit_wallet  = TREASURY_WALLET
            credit_wallet = CARD_FLOAT_ACCT
        else:
            debit_wallet  = CARD_FLOAT_ACCT
            credit_wallet = TREASURY_WALLET

        for wallet, dr_cr, amt in [
            (debit_wallet,  "DEBIT",  amount_dollars),
            (credit_wallet, "CREDIT", amount_dollars),
        ]:
            cur.execute("""
                INSERT INTO ledger_entries
                    (id, transaction_id, wallet_id, direction,
                     amount, currency, description, reference,
                     idempotency_key, created_at)
                VALUES
                    (%s::uuid, %s::uuid, %s::uuid, %s,
                     %s, 'USD', %s, %s, %s, NOW())
            """, (
                str(uuid.uuid4()), tx_id, wallet,
                dr_cr, amt, description, reference, idempotency_key
            ))

        # Update settled_balance — trigger handles available_balance
        if direction == "DEBIT":
            cur.execute("""
                UPDATE wallets
                SET settled_balance = settled_balance - %s
                WHERE id = %s::uuid
            """, (amount_dollars, TREASURY_WALLET))
        else:
            cur.execute("""
                UPDATE wallets
                SET settled_balance = settled_balance + %s
                WHERE id = %s::uuid
            """, (amount_dollars, TREASURY_WALLET))

        conn.commit()
        cur.close()
        conn.close()
        return {"success": True, "transaction_id": tx_id,
                "amount": amount_dollars}

    except Exception as e:
        return {"success": False, "error": str(e)}

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def get_balance():
    """Stripe account balance."""
    result = stripe_request("GET", "balance")
    print("\n  STRIPE BALANCE")
    print("  " + "─" * 40)
    for bal in result.get("available", []):
        print(f"  Available: ${bal['amount']/100:.2f} {bal['currency'].upper()}")
    for bal in result.get("pending", []):
        print(f"  Pending:   ${bal['amount']/100:.2f} {bal['currency'].upper()}")
    print()
    return result

def create_card(cardholder_name: str = "Thomas Lee Harvey",
                spending_limit_cents: int = 100000,
                currency: str = "usd") -> dict:
    """
    Create a real virtual Visa card via Stripe Issuing.
    Records issuance in omega_bank ledger.
    """
    print(f"\n  Creating virtual card for {cardholder_name}...")

    # 1. Create or get cardholder
    cardholder = stripe_request("POST", "issuing/cardholders", {
        "name":         cardholder_name,
        "email":        "simpl3hoods@gmail.com",
        "type":         "individual",
        "billing[address][line1]":      "123 Omega St",
        "billing[address][city]":       "Atlanta",
        "billing[address][state]":      "GA",
        "billing[address][postal_code]": "30301",
        "billing[address][country]":    "US",
    })
    cardholder_id = cardholder["id"]
    print(f"  Cardholder: {cardholder_id}")

    # 2. Issue card
    card = stripe_request("POST", "issuing/cards", {
        "cardholder":   cardholder_id,
        "currency":     currency,
        "type":         "virtual",
        "spending_controls[spending_limits][0][amount]":   spending_limit_cents,
        "spending_controls[spending_limits][0][interval]": "monthly",
    })

    card_id  = card["id"]
    card_last4 = card.get("last4", "????")
    print(f"  Card issued: {card_id} (****{card_last4})")

    # 3. Get full card details (PAN only available immediately after creation)
    card_details = stripe_request(
        "GET", f"issuing/cards/{card_id}?expand[]=number&expand[]=cvc")
    pan = card_details.get("number", "hidden")
    cvc = card_details.get("cvc", "hidden")
    exp = f"{card_details.get('exp_month','??')}/{card_details.get('exp_year','??')}"

    # 4. Record in omega_bank ledger
    idem_key    = hashlib.sha256(card_id.encode()).hexdigest()[:32]
    ledger_result = post_ledger_entry(
        description     = f"Stripe Issuing card created: ****{card_last4}",
        amount_cents    = spending_limit_cents,
        direction       = "DEBIT",
        reference       = card_id,
        idempotency_key = idem_key,
    )

    print(f"\n  ✅ CARD READY")
    print(f"  Card ID  : {card_id}")
    print(f"  PAN      : {pan}")
    print(f"  CVC      : {cvc}")
    print(f"  Expires  : {exp}")
    print(f"  Limit    : ${spending_limit_cents/100:.2f}/month")
    print(f"  Ledger   : {ledger_result}")
    print()

    return {
        "card_id":   card_id,
        "pan":       pan,
        "cvc":       cvc,
        "expires":   exp,
        "last4":     card_last4,
        "ledger":    ledger_result,
    }

def list_cards():
    """List all issued cards."""
    result = stripe_request("GET", "issuing/cards?limit=20")
    cards  = result.get("data", [])
    print(f"\n  ISSUED CARDS ({len(cards)})")
    print("  " + "─" * 54)
    for c in cards:
        status = c.get("status", "?")
        icon   = "✅" if status == "active" else "⚠️ "
        print(f"  {icon} ****{c.get('last4','????')}  "
              f"{c.get('exp_month','?')}/{c.get('exp_year','?')}  "
              f"{status:<10}  {c['id']}")
    print()
    return cards

def get_card(card_id: str):
    """Get single card with full details."""
    result = stripe_request(
        "GET",
        f"issuing/cards/{card_id}?expand[]=number&expand[]=cvc"
    )
    print(f"\n  CARD: {card_id}")
    print(f"  PAN    : {result.get('number', 'hidden')}")
    print(f"  CVC    : {result.get('cvc', 'hidden')}")
    print(f"  Exp    : {result.get('exp_month','?')}/{result.get('exp_year','?')}")
    print(f"  Status : {result.get('status','?')}")
    print(f"  Last4  : {result.get('last4','?')}")
    print()
    return result

def reconcile():
    """
    Pull recent Stripe Issuing transactions and reconcile
    against omega_bank ledger. Posts any missing entries.
    """
    print("\n  RECONCILING Stripe → omega_bank...")
    txns = stripe_request(
        "GET", "issuing/transactions?limit=50")
    data = txns.get("data", [])
    print(f"  Found {len(data)} Stripe transactions")

    reconciled = 0
    for tx in data:
        amount    = abs(tx.get("amount", 0))
        direction = "DEBIT" if tx.get("amount", 0) < 0 else "CREDIT"
        idem_key  = hashlib.sha256(tx["id"].encode()).hexdigest()[:32]
        desc      = f"Stripe: {tx.get('merchant_data',{}).get('name','unknown')}"

        result = post_ledger_entry(
            description     = desc,
            amount_cents    = amount,
            direction       = direction,
            reference       = tx["id"],
            idempotency_key = idem_key,
        )
        if result.get("success"):
            reconciled += 1
            print(f"  ✅ ${amount/100:.2f} {direction} — {desc}")
        else:
            err = result.get("error", "")
            if "duplicate" in err.lower() or "unique" in err.lower():
                print(f"  ⏭️  Already reconciled: {tx['id'][:16]}")
            else:
                print(f"  ❌ Failed: {err}")

    print(f"\n  Reconciled {reconciled}/{len(data)} transactions\n")

# ---------------------------------------------------------------------------
# Webhook listener — receives Stripe events on port 5010
# ---------------------------------------------------------------------------
def start_webhook_listener():
    """
    Raw socket webhook listener.
    Stripe sends events here — auto-reconciles spend to ledger.
    Point Stripe dashboard webhook to: http://23.162.0.62:5010/webhook
    """
    import socket, threading

    def verify_signature(payload: bytes, sig_header: str) -> bool:
        if not STRIPE_WEBHOOK:
            return True   # skip verification if secret not set
        try:
            ts    = [p.split("=")[1] for p in sig_header.split(",")
                     if p.startswith("t=")][0]
            sigs  = [p.split("=", 1)[1] for p in sig_header.split(",")
                     if p.startswith("v1=")]
            signed = f"{ts}.".encode() + payload
            expected = hmac.new(
                STRIPE_WEBHOOK.encode(), signed, hashlib.sha256
            ).hexdigest()
            return any(hmac.compare_digest(expected, s) for s in sigs)
        except Exception:
            return False

    def handle(conn, addr):
        try:
            raw = b""
            conn.settimeout(10)
            while True:
                chunk = conn.recv(65536)
                if not chunk: break
                raw += chunk
                if b"\r\n\r\n" in raw:
                    hdr_end = raw.find(b"\r\n\r\n")
                    cl      = 0
                    for line in raw[:hdr_end].decode(errors="replace").split("\r\n")[1:]:
                        if line.lower().startswith("content-length:"):
                            cl = int(line.split(":")[1].strip())
                    if len(raw) >= hdr_end + 4 + cl:
                        break

            hdr_end  = raw.find(b"\r\n\r\n")
            headers  = {}
            for line in raw[:hdr_end].decode(errors="replace").split("\r\n")[1:]:
                if ": " in line:
                    k, v = line.split(": ", 1)
                    headers[k.lower()] = v
            body = raw[hdr_end + 4:]

            sig = headers.get("stripe-signature", "")
            if not verify_signature(body, sig):
                conn.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
                return

            event = json.loads(body)
            etype = event.get("type", "")
            print(f"[WEBHOOK] {etype}")

            # Auto-reconcile card spend
            if etype == "issuing_transaction.created":
                tx     = event["data"]["object"]
                amount = abs(tx.get("amount", 0))
                dirn   = "DEBIT" if tx.get("amount", 0) < 0 else "CREDIT"
                ikey   = hashlib.sha256(tx["id"].encode()).hexdigest()[:32]
                desc   = (f"Stripe: "
                          f"{tx.get('merchant_data',{}).get('name','unknown')}")
                result = post_ledger_entry(desc, amount, dirn, tx["id"], ikey)
                print(f"[WEBHOOK] Ledger: {result}")

            conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK")
        except Exception as e:
            print(f"[WEBHOOK ERROR] {e}")
        finally:
            conn.close()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", WEBHOOK_PORT))
    srv.listen(32)
    print(f"\n  Stripe webhook listener on port {WEBHOOK_PORT}")
    print(f"  Point Stripe to: https://antivirus-configurations-generic-basin.trycloudflare.com/webhook/stripe\n")

    while True:
        try:
            conn, addr = srv.accept()
            threading.Thread(
                target=handle, args=(conn, addr), daemon=True
            ).start()
        except KeyboardInterrupt:
            break

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if not STRIPE_SECRET:
        print("❌ STRIPE_SECRET_KEY not set in environment")
        print("   Add to ~/.env: STRIPE_SECRET_KEY=sk_live_...")
        sys.exit(1)

    cmd = sys.argv[1] if len(sys.argv) > 1 else "balance"

    if cmd == "balance":
        get_balance()
    elif cmd == "create_card":
        limit = int(sys.argv[2]) * 100 if len(sys.argv) > 2 else 100000
        create_card(spending_limit_cents=limit)
    elif cmd == "list_cards":
        list_cards()
    elif cmd == "card" and len(sys.argv) > 2:
        get_card(sys.argv[2])
    elif cmd == "reconcile":
        reconcile()
    elif cmd == "webhook":
        start_webhook_listener()
    else:
        print("Usage: python3 omega_stripe_bridge.py "
              "[balance|create_card|list_cards|card <id>|reconcile|webhook]")
