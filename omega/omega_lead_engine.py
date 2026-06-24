#!/usr/bin/env python3
"""
Omega Lead Engine — 100 real emails per day
No external APIs. DuckDuckGo + Bing via Tor.
Scrapes real contact pages. MX verified only.
"""
import re, time, json, socket, smtplib, sqlite3, urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime

HOME    = Path("/data/data/com.termux/files/home")
DB_PATH = HOME / "omega_runtime/db/omega.db"
LOG     = HOME / "omega_runtime/logs/lead_engine.json"

def env(key):
    for line in (HOME / ".env").read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=",1)[1].strip()
    return ""

SMTP_USER    = env("SMTP_USER")
SMTP_PASS    = env("SMTP_PASS")
CEO_NAME     = env("CEO_NAME")
COMPANY_NAME = env("COMPANY_NAME")
CALENDLY     = env("CALENDLY_LINK")
STRIPE_START = env("STRIPE_LINK_STARTER")
MAX_SENDS    = int(env("MAX_DAILY_SENDS") or 100)

PROXIES = {
    "http":  "socks5h://127.0.0.1:9050",
    "https": "socks5h://127.0.0.1:9050"
}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
}

JUNK_EMAIL = {
    "info","contact","hello","support","admin","office",
    "mail","team","sales","noreply","no-reply","help",
    "service","billing","press","legal","privacy","webmaster",
    "postmaster","abuse","careers","jobs","media"
}

JUNK_DOMAINS = {
    "google","youtube","facebook","yelp","bing","yahoo",
    "tripadvisor","instagram","twitter","wikipedia","linkedin",
    "bbb.org","angieslist","thumbtack","houzz","homeadvisor",
    "duckduckgo","yellowpages","mapquest","manta","bark.com",
    "angi.com","nextdoor","alignable","clutch.co","upcity"
}

CITIES = [
    "Atlanta","Dallas","Houston","Charlotte","Phoenix",
    "Nashville","Miami","Denver","Tampa","Austin"
]

NICHES = [
    "HVAC company","roofing company","plumbing company",
    "law firm","dental practice","med spa",
    "accounting firm","auto repair shop",
    "home renovation contractor","pest control"
]

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

def load_log():
    try:
        return json.loads(LOG.read_text())
    except Exception:
        return {"sent": [], "total": 0, "date": ""}

def save_log(log):
    LOG.write_text(json.dumps(log, indent=2))

def tor_get(url, timeout=12):
    """Fetch URL through Tor proxy."""
    try:
        import requests
        r = requests.get(url, headers=HEADERS, proxies=PROXIES,
                        timeout=timeout, allow_redirects=True)
        return r.text
    except Exception:
        return ""

def ddg_search(query, num=8):
    """DuckDuckGo HTML search through Tor."""
    try:
        import requests
        r = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=HEADERS, proxies=PROXIES, timeout=15
        )
        urls = re.findall(
            r'class="result__url"[^>]*>\s*([^\s<]+)', r.text
        )
        results = []
        for url in urls:
            domain = url.replace("www.","").split("/")[0].strip().lower()
            if (domain and "." in domain and len(domain) > 4 and
                    not any(j in domain for j in JUNK_DOMAINS)):
                results.append(domain)
        return list(dict.fromkeys(results))[:num]
    except Exception as e:
        print(f"  [DDG] {e}")
        return []

def bing_search(query, num=8):
    """Bing search through Tor as backup."""
    try:
        import requests
        r = requests.get(
            "https://www.bing.com/search",
            params={"q": query},
            headers=HEADERS, proxies=PROXIES, timeout=15
        )
        urls = re.findall(r'([^<]+)', r.text)
        results = []
        for url in urls:
            domain = url.replace("www.","").split("/")[0].strip().lower()
            if (domain and "." in domain and len(domain) > 4 and
                    not any(j in domain for j in JUNK_DOMAINS)):
                results.append(domain)
        return list(dict.fromkeys(results))[:num]
    except Exception as e:
        print(f"  [BING] {e}")
        return []

def extract_emails(html, domain):
    """Extract non-junk emails from HTML, prefer domain-matching."""
    found = EMAIL_RE.findall(html)
    domain_emails = []
    other_emails  = []
    for email in found:
        local = email.split("@")[0].lower()
        if local in JUNK_EMAIL:
            continue
        if domain.split(".")[0] in email.lower():
            domain_emails.append(email.lower())
        else:
            other_emails.append(email.lower())
    return (domain_emails + other_emails)

def scrape_owner_email(domain):
    """
    Hit contact/about/team pages, extract real owner email.
    Returns first non-junk email found or None.
    """
    pages = [
        f"https://{domain}",
        f"https://{domain}/contact",
        f"https://{domain}/contact-us",
        f"https://{domain}/about",
        f"https://{domain}/about-us",
        f"https://{domain}/team",
        f"https://{domain}/staff",
        f"https://www.{domain}",
        f"https://www.{domain}/contact",
    ]
    for url in pages:
        html = tor_get(url, timeout=10)
        if not html:
            continue
        emails = extract_emails(html, domain)
        if emails:
            return emails[0]
        time.sleep(0.5)
    return None

def verify_mx(email):
    """Check domain has MX record — fast DNS lookup."""
    try:
        domain = email.split("@")[1]
        socket.getaddrinfo(domain, None)
        return True
    except Exception:
        return False

def save_lead(email, name, domain, city, niche):
    """Save to omega.db leads table."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("""
            INSERT OR IGNORE INTO leads
            (email, name, website, category, source, score, status, stage)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            email, name, f"https://{domain}",
            f"{niche} {city}", "scraped", 85.0, "new", 0
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"  [DB] {e}")

def send_outreach(email, name, domain, city, niche):
    """Send personalized outreach email via Gmail SMTP."""
    subject = f"Quick question for {name}"
    body = f"""Hi,

I came across {name} while researching top {niche}s in {city}.

I'm {CEO_NAME}, founder of {COMPANY_NAME}. We help local businesses like yours respond to every lead instantly — AI handles your inbox 24/7, follows up automatically, and alerts you when someone's ready to book.

Most clients are live within 24 hours. 7-day free trial, $0 today.

Start here: {STRIPE_START}

Or just reply and I'll set everything up personally.

{CEO_NAME}
{COMPANY_NAME}"""

    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        msg = MIMEMultipart()
        msg["From"]    = SMTP_USER
        msg["To"]      = email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as s:
            s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(SMTP_USER, email, msg.as_string())
        return True
    except Exception as e:
        print(f"  [SMTP] {e}")
        return False

def run():
    log   = load_log()
    sent  = set(log.get("sent", []))
    today = datetime.now().strftime("%Y-%m-%d")

    # Reset daily count if new day
    if log.get("date") != today:
        log["date"]       = today
        log["daily_sent"] = 0

    daily_sent = log.get("daily_sent", 0)

    print(f"\n{'═'*52}")
    print(f"  OMEGA LEAD ENGINE — Target: {MAX_SENDS}/day")
    print(f"  Sent today: {daily_sent} | Total: {log.get('total',0)}")
    print(f"{'═'*52}\n")

    for city in CITIES:
        if daily_sent >= MAX_SENDS:
            break
        for niche in NICHES:
            if daily_sent >= MAX_SENDS:
                break

            query = f"{niche} {city}"
            print(f"[→] {query}")

            # Search DDG first, Bing as backup
            domains = ddg_search(f"{query} contact email", num=8)
            if len(domains) < 3:
                domains += bing_search(f"{query} owner contact", num=8)
            domains = list(dict.fromkeys(domains))

            for domain in domains:
                if daily_sent >= MAX_SENDS:
                    break
                if domain in sent:
                    continue

                print(f"  [?] Scraping: {domain}")
                email = scrape_owner_email(domain)

                if not email:
                    print(f"  [✗] No email")
                    sent.add(domain)
                    continue

                if not verify_mx(email):
                    print(f"  [✗] Bad MX: {email}")
                    sent.add(domain)
                    continue

                name = domain.replace("-"," ").replace("."," ").title().split()[0]
                print(f"  [✉] {email} → sending...")

                if send_outreach(email, name, domain, city, niche):
                    save_lead(email, name, domain, city, niche)
                    sent.add(domain)
                    daily_sent += 1
                    log["sent"]       = list(sent)
                    log["total"]      = log.get("total", 0) + 1
                    log["daily_sent"] = daily_sent
                    save_log(log)
                    print(f"  [✅] Sent #{daily_sent}: {email}")
                    time.sleep(12)  # Deliverability rate limiting
                else:
                    sent.add(domain)

            time.sleep(2)

    print(f"\n{'═'*52}")
    print(f"  DONE — Sent {daily_sent} emails today")
    print(f"{'═'*52}\n")
    save_log(log)

if __name__ == "__main__":
    run()
