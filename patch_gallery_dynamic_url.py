#!/usr/bin/env python3
with open("/data/data/com.termux/files/home/omega_gallery.html", "r") as f:
    content = f.read()

old = 'const PROVENANCE_API = "https://pursue-carriers-humanities-shipped.trycloudflare.com";'

new = '''let PROVENANCE_API = "http://127.0.0.1:8082";
// Auto-fetch current tunnel URL from broker
(async () => {
  try {
    const r = await fetch("http://127.0.0.1:8085/current-all");
    const d = await r.json();
    if (d.api) PROVENANCE_API = d.api;
  } catch(e) {}
})();'''

if old not in content:
    print("ERROR: PROVENANCE_API line not found")
    raise SystemExit(1)

content = content.replace(old, new, 1)

with open("/data/data/com.termux/files/home/omega_gallery.html", "w") as f:
    f.write(content)

print("Patch applied")
