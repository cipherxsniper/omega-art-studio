#!/usr/bin/env python3
with open("/data/data/com.termux/files/home/omega_gallery.html", "r") as f:
    content = f.read()

# Patch 1: Replace green theme with surrealist dark palette
replacements = [
    ("#00e89a", "#C9A84C"),      # green accent → antique gold
    ("#5d8c79", "#8B7355"),      # muted green label → aged bronze
    ("#e8fff2", "#F0E6D3"),      # green-white text → warm parchment
    ("#0a1a12", "#0D0B0E"),      # dark green bg → near-black void
    ("#0f2318", "#13100F"),      # deep green → dark charcoal
    ("#1a3d28", "#1C1612"),      # mid green → dark umber
    ("rgba(0,232,154", "rgba(201,168,76"),   # green glow → gold glow
    ("rgba(0,232,154,.15)", "rgba(201,168,76,.15)"),
    ("border:1px solid #00e89a", "border:1px solid #C9A84C"),
]

for old, new in replacements:
    content = content.replace(old, new)

# Patch 2: Add COA + price + buy button to card back
PRICE_MAP = {
    "Impossible Diamond": "$2,500",
    "Black Diamond": "$500",
    "Super Rare": "$150",
    "Rare": "$75",
    "Medium": "$35",
    "Common": "$15",
}

old_back = "        '<div class=\"face face-back\">' +\n          '<div class=\"back-row\"><div class=\"back-label\">Title</div><div class=\"back-value\">' + t.title + '</div></div>' +"

new_back = """        '<div class=\"face face-back\">' +
          '<div style=\"text-align:center;border-bottom:1px solid #C9A84C;margin-bottom:8px;padding-bottom:6px;\">' +
            '<div style=\"font-family:\\'Cormorant Garamond\\',serif;font-size:11px;letter-spacing:2px;color:#C9A84C;text-transform:uppercase;\">Certificate of Authenticity</div>' +
            '<div style=\"font-size:8px;color:#8B7355;margin-top:2px;font-style:italic;\">Omega Art Studio · Thomas Lee Harvey</div>' +
          '</div>' +
          '<div class=\"back-row\"><div class=\"back-label\">Title</div><div class=\"back-value\">' + t.title + '</div></div>' +"""

if old_back not in content:
    print("ERROR: card back anchor not found")
    raise SystemExit(1)

content = content.replace(old_back, new_back, 1)

# Add price + buy button after OM109 row
old_om109 = "          '<div class=\"back-row\"><div class=\"back-label\">OM109</div><div class=\"back-value\">' + (t.om109_fingerprint||'').substring(0,32) + '...</div></div>' +"

price_js = """          '<div class=\"back-row\"><div class=\"back-label\">OM109</div><div class=\"back-value\">' + (t.om109_fingerprint||'').substring(0,32) + '...</div></div>' +
          '<div class=\"back-row\"><div class=\"back-label\">Chain Hash</div><div class=\"back-value\">' + (t.chain_hash||'').substring(0,32) + '...</div></div>' +
          '<div style=\"margin-top:10px;border-top:1px solid #3a2e1e;padding-top:10px;\">' +
            (t.stripe_payment_link ?
              '<a href=\"' + t.stripe_payment_link + '\" target=\"_blank\" style=\"display:block;text-align:center;background:#C9A84C;color:#0D0B0E;padding:8px;font-size:10px;letter-spacing:2px;text-decoration:none;font-weight:bold;text-transform:uppercase;border-radius:2px;\">Purchase · ' + ({"Impossible Diamond":"$2,500","Black Diamond":"$500","Super Rare":"$150","Rare":"$75","Medium":"$35","Common":"$15"}[t.rarity]||"$15") + '</a>'
              : '<div style=\"text-align:center;color:#8B7355;font-size:9px;\">Not for sale</div>'
            ) +
          '</div>' +"""

if old_om109 not in content:
    print("ERROR: OM109 row not found")
    raise SystemExit(1)

content = content.replace(old_om109, price_js, 1)

with open("/data/data/com.termux/files/home/omega_gallery.html", "w") as f:
    f.write(content)

print("Patch applied")
