#!/usr/bin/env python3
with open("/data/data/com.termux/files/home/omega_nft_webhook.py", "r") as f:
    lines = f.readlines()

# Find the function start and end
start = None
end = None
for i, line in enumerate(lines):
    if "def _send_coa_email(" in line:
        start = i
    if start and i > start and line.startswith("def ") and "send_coa" not in line:
        end = i
        break

if start is None or end is None:
    print(f"ERROR: start={start} end={end}")
    raise SystemExit(1)

print(f"Replacing lines {start+1}-{end} ({end-start} lines)")

new_func = '''def _send_coa_email(token, buyer, image_path, receipt_hash="", passport_url=""):
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    if not smtp_user or not smtp_pass:
        print("[nft_webhook] SMTP not configured")
        return False

    rarity = RARITY_LABEL.get(token.get("rarity", "common"), token.get("rarity", ""))
    tid = token["token_id"]
    coll = token["collection"].replace("_", " ").title()
    title = token.get("title", f"Token #{tid}")
    fp = token.get("om109_fingerprint", "")
    ch = token.get("chain_hash", "")
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    quote = _quote()
    verify_url = _live_verify_url(token["collection"], tid)
    receipt_line = f"\\nReceipt  : {_live_receipt_url(receipt_hash)}" if receipt_hash else ""
    passport_line = f"\\nPassport : {passport_url}" if passport_url else ""

    body = (
        "\\n"
        + "-" * 42 + "\\n"
        + "CERTIFICATE OF AUTHENTICITY\\n"
        + "Omega Art Studio\\n"
        + "-" * 42 + "\\n\\n"
        + f"Title      : {title}\\n"
        + f"Collection : {coll}\\n"
        + f"Token ID   : {tid}\\n"
        + f"Rarity     : {rarity}\\n"
        + f"OM109      : {fp}\\n"
        + f"Chain Hash : {ch}\\n"
        + f"Recorded   : {ts}\\n\\n"
        + "-" * 42 + "\\n"
        + "CUSTODIAL NOTICE\\n"
        + "-" * 42 + "\\n"
        + "This is a digital asset. The PNG, this certificate,\\n"
        + "and the OM109 fingerprint are your responsibility.\\n"
        + "Omega provides the provenance. You hold the asset.\\n\\n"
        + f"Verify   : {verify_url}"
        + receipt_line
        + passport_line
        + "\\n\\n"
        + f'"{quote}"\\n\\n'
        + "Thomas Lee Harvey\\n"
        + "CEO & Founder, Omega Art Studio\\n"
    )

    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = buyer
    msg["Subject"] = f"Your {rarity} - {title} | Certificate of Authenticity"
    msg.attach(MIMEText(body, "plain"))
    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition",
                        f\'attachment; filename="{token["collection"]}_{tid}.png"\')
        msg.attach(part)
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as s:
            s.starttls()
            s.login(smtp_user, smtp_pass)
            s.sendmail(smtp_user, buyer, msg.as_string())
        print(f"[nft_webhook] COA emailed to {buyer}")
        return True
    except Exception as e:
        print(f"[nft_webhook] Email failed: {e}")
        return False

'''

lines[start:end] = [new_func]

with open("/data/data/com.termux/files/home/omega_nft_webhook.py", "w") as f:
    f.writelines(lines)
print("Patch applied")
