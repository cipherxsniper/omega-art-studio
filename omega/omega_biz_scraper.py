#!/usr/bin/env python3
"""
Omega Business Scraper — 5000 real businesses
Sources: Better Business Bureau, Chamber of Commerce,
         state contractor license directories
No search engines. Direct directory scraping via Tor.
"""
import urllib.request, re, sqlite3, time, json, socket
import socks
from pathlib import Path

HOME = Path("/data/data/com.termux/files/home")
DB   = HOME / "omega_runtime/db/omega.db"

def env(k):
    for line in (HOME / ".env").read_text().splitlines():
        if line.startswith(f"{k}="):
            return line.split("=",1)[1].strip()
    return ""

# Route through Tor
socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 9050)
socket.socket = socks.socksocket

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
JUNK     = {"noreply","no-reply","support","admin","info",
            "contact","hello","sales","billing","press",
            "legal","privacy","webmaster","postmaster"}

AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0",
]

import random

def fetch(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": random.choice(AGENTS),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""

def extract_email(html):
    emails = EMAIL_RE.findall(html)
    for e in emails:
        local = e.split("@")[0].lower()
        if local not in JUNK and "." in e.split("@")[1]:
            return e.lower()
    return None

def mx_ok(email):
    try:
        socket.getaddrinfo(email.split("@")[1], None)
        return True
    except Exception:
        return False

def scrape_contact_pages(domain):
    for path in ["", "/contact", "/contact-us", "/about", "/about-us", "/team"]:
        html = fetch(f"https://{domain}{path}")
        if html:
            email = extract_email(html)
            if email and mx_ok(email):
                return email
        time.sleep(0.5)
    return None

def save_lead(name, email, domain, category, city):
    try:
        conn = sqlite3.connect(str(DB))
        conn.execute("""
            INSERT OR IGNORE INTO leads
            (email, name, website, category, source, score, status, stage)
            VALUES (?,?,?,?,?,?,?,?)
        """, (email, name, f"https://{domain}",
              f"{category} {city}", "scraped", 85.0, "new", 0))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

# ── Directory sources ──────────────────────────────────────

def scrape_bbb(city, category):
    """BBB directory — real businesses with real contact info."""
    results = []
    city_slug = city.lower().replace(" ", "-")
    cat_slug  = category.lower().replace(" ", "-")
    url = f"https://www.bbb.org/search?find_text={cat_slug}&find_loc={city_slug}"
    html = fetch(url)
    if not html:
        return results
    # Extract business names and URLs
    links = re.findall(r'href="(/profile/[^"]+)"', html)
    for link in links[:10]:
        try:
            biz_html = fetch(f"https://www.bbb.org{link}")
            name_match = re.search(r'<h1[^>]*>([^<]+)</h1>', biz_html)
            website_match = re.search(r'href="(https?://(?!.*bbb\.org)[^"]+)"[^>]*>\s*(?:Website|Visit)', biz_html)
            if name_match and website_match:
                name   = name_match.group(1).strip()
                site   = website_match.group(1).strip()
                domain = site.replace("https://","").replace("http://","").replace("www.","").split("/")[0]
                results.append({"name": name, "domain": domain, "city": city, "category": category})
            time.sleep(1)
        except Exception:
            pass
    return results

def scrape_chamberofcommerce(city, category):
    """Chamber of Commerce directory."""
    results = []
    city_slug = city.lower().replace(" ","+")
    cat_slug  = category.lower().replace(" ","+")
    url = f"https://www.chamberofcommerce.com/search?q={cat_slug}&location={city_slug}"
    html = fetch(url)
    if not html:
        return results
    domains = re.findall(r'href="https?://(?!.*chamberofcommerce)([^/"]+)', html)
    seen = set()
    for domain in domains:
        domain = domain.replace("www.","").strip()
        if domain and "." in domain and domain not in seen and len(domain) > 4:
            seen.add(domain)
            results.append({
                "name": domain.split(".")[0].title(),
                "domain": domain,
                "city": city,
                "category": category
            })
    return results[:10]

def scrape_manta(city, category):
    """Manta business directory."""
    results = []
    city_slug = city.lower().replace(" ","-")
    cat_slug  = category.lower().replace(" ","-")
    url = f"https://www.manta.com/mb/{city_slug}/{cat_slug}"
    html = fetch(url)
    if not html:
        return results
    links = re.findall(r'href="(/c/[^"]+)"', html)
    for link in links[:8]:
        try:
            biz_html = fetch(f"https://www.manta.com{link}")
            name  = re.search(r'<h1[^>]*>([^<]+)</h1>', biz_html)
            site  = re.search(r'href="(https?://(?!.*manta\.com)[^"]+)"', biz_html)
            if name and site:
                domain = site.group(1).replace("https://","").replace("http://","").replace("www.","").split("/")[0]
                results.append({
                    "name": name.group(1).strip(),
                    "domain": domain,
                    "city": city,
                    "category": category
                })
            time.sleep(0.8)
        except Exception:
            pass
    return results

# ── Main run ───────────────────────────────────────────────

CITIES = [
    "Atlanta GA", "Dallas TX", "Houston TX",
    "Charlotte NC", "Phoenix AZ", "Nashville TN",
    "Miami FL", "Denver CO", "Tampa FL", "Austin TX"
]

CATEGORIES = [
    "HVAC", "roofing", "plumbing", "law firm",
    "dental", "med spa", "accounting", "auto repair",
    "landscaping", "pest control", "electrical", "painting"
]

def run():
    found   = 0
    emailed = 0
    conn    = sqlite3.connect(str(DB))
    sent_domains = set(
        r[0].split("/")[-1] for r in
        conn.execute("SELECT website FROM leads WHERE source='scraped'").fetchall()
    )
    conn.close()

    print(f"\n{'═'*52}")
    print(f"  OMEGA BUSINESS SCRAPER — Target: 5000 leads")
    print(f"  Sources: BBB, Chamber of Commerce, Manta")
    print(f"{'═'*52}\n")

    for city in CITIES:
        for category in CATEGORIES:
            print(f"[→] {category} in {city}")

            # Try all three directory sources
            businesses = []
            businesses += scrape_bbb(city, category)
            businesses += scrape_chamberofcommerce(city, category)
            businesses += scrape_manta(city, category)

            for biz in businesses:
                domain = biz["domain"]
                if not domain or domain in sent_domains:
                    continue

                print(f"  [?] {biz['name']} — {domain}")
                email = scrape_contact_pages(domain)

                if not email:
                    print(f"  [✗] No email")
                    sent_domains.add(domain)
                    continue

                if save_lead(biz["name"], email, domain,
                            biz["category"], biz["city"]):
                    found += 1
                    sent_domains.add(domain)
                    print(f"  [✅] {email} saved ({found} total)")

                time.sleep(2)

    print(f"\n{'═'*52}")
    print(f"  DONE — {found} leads saved to database")
    print(f"{'═'*52}\n")

if __name__ == "__main__":
    run()
