#!/usr/bin/env python3
"""
OMEGA LEAD RUNNER — 100 Email Batch
Pulls businesses from Google CSE, finds owner emails via SerpAPI, sends outreach
"""
import os, time, json, requests, smtplib, re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

# ── Config from .env ─────────────────────────────────────
HOME = Path("/data/data/com.termux/files/home")

def env(key):
    for line in (HOME / ".env").read_text().splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip()
    return ""

SERPAPI_KEY   = env("SERPAPI_API_KEY")
GOOGLE_KEY    = env("GOOGLE_CSE_KEY")
GOOGLE_CX     = env("GOOGLE_CSE_CX")
SMTP_USER     = env("SMTP_USER")
SMTP_PASS     = env("SMTP_PASS")
CEO_NAME      = env("CEO_NAME")
COMPANY_NAME  = env("COMPANY_NAME")
CALENDLY      = env("CALENDLY_LINK")
MAX_SENDS     = int(env("MAX_DAILY_SENDS") or 100)
CITIES        = env("LEAD_CITIES").split(",")
SCORE_MIN     = int(env("SEND_SCORE_THRESHOLD") or 60)

LOG_FILE      = HOME / "omega_runtime/logs/lead_runner.json"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# ── Load sent log ─────────────────────────────────────────
def load_log():
    try:
        return json.loads(LOG_FILE.read_text())
    except:
        return {"sent": [], "total": 0}

def save_log(log):
    LOG_FILE.write_text(json.dumps(log, indent=2))

# ── Find businesses via Google CSE ────────────────────────
PROXIES = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
JUNK_DOMAINS = ["google","youtube","facebook","yelp","bing","yahoo",
                "tripadvisor","instagram","twitter","wikipedia","linkedin",
                "bbb.org","angieslist","thumbtack","houzz","homeadvisor",
                "duckduckgo","contactout","yellowpages","mapquest"]

def find_businesses(niche, city, num=10):
    try:
        r = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": f"{niche} {city} contact email site:.com"},
            headers=HEADERS, proxies=PROXIES, timeout=15
        )
        links = re.findall(r'class="result__url"[^>]*>\s*([^\s<]+)', r.text)
        seen = set()
        results = []
        for link in links:
            domain = link.replace("www.","").split("/")[0].strip()
            if domain not in seen and not any(j in domain for j in JUNK_DOMAINS) and "." in domain and len(domain) > 4:
                seen.add(domain)
                results.append({"name": f"{niche.title()} - {city.title()}", "domain": domain, "city": city})
        return results[:num]
    except Exception as e:
        print(f"  [DDG ERROR] {e}")
        return []

def scrape_site_email(domain):
    email_re = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    junk = ["info","contact","hello","support","admin","noreply","no-reply","mail","team"]
    for url in [f"https://{domain}", f"https://{domain}/contact", f"https://{domain}/about"]:
        try:
            r = requests.get(url, timeout=8, headers=HEADERS, proxies=PROXIES)
            for email in email_re.findall(r.text):
                local = email.split("@")[0].lower()
                if local not in junk and "." in email.split("@")[1]:
                    return email.lower()
        except:
            pass
    return None

# ── Find owner email via SerpAPI ──────────────────────────
def find_email(business_name, domain):
    email_re = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    junk = ["info","contact","hello","support","admin","office","mail","team","sales","noreply"]
    queries = [
        f'"{business_name}" owner email',
        f'"{business_name}" CEO contact {domain}',
    ]
    for query in queries:
        try:
            r = requests.get(
                "https://serpapi.com/search",
                params={"api_key": SERPAPI_KEY, "engine": "google",
                        "q": query, "num": 5},
                timeout=15
            )
            for result in r.json().get("organic_results", []):
                snippet = result.get("snippet", "") + result.get("title", "")
                for email in email_re.findall(snippet):
                    local = email.split("@")[0].lower()
                    if local not in junk and (domain in email or "@" in email):
                        return email.lower()
            time.sleep(0.5)
        except:
            pass
    return None

# ── Send outreach email ───────────────────────────────────
def send_email_old(to_email, business_name, city):
    subject = f"Quick question about {business_name}'s growth"
    body = f"""Hi,

I came across {business_name} and wanted to reach out directly.

I'm {CEO_NAME}, founder of {COMPANY_NAME}. We help businesses in {city} automate their operations — client onboarding, payments, follow-ups, and reporting — all running automatically so you can focus on growth.

Most of our clients see results within the first 30 days.

Would you be open to a quick 15-minute call this week?

{CALENDLY}

Best,
{CEO_NAME}
{COMPANY_NAME}
"""
    try:
        msg = MIMEMultipart()
        msg["From"]    = SMTP_USER
        msg["To"]      = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as s:
            s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(SMTP_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"  [SMTP ERROR] {e}")
        return False

# ── Main batch runner ─────────────────────────────────────
def run():
    log    = load_log()
    sent   = set(log["sent"])
    count  = 0
    niches = ["restaurant","salon","gym","plumber","electrician",
              "lawyer","dentist","real estate","contractor","auto repair"]

    print(f"\n{'='*55}")
    print(f"  OMEGA LEAD RUNNER — Target: {MAX_SENDS} emails")
    print(f"  Cities: {', '.join(CITIES[:4])}...")
    print(f"{'='*55}\n")

    for city in CITIES:
        if count >= MAX_SENDS:
            break
        for niche in niches:
            if count >= MAX_SENDS:
                break
            print(f"[→] Searching: {niche} in {city}")
            businesses = find_businesses(niche, city, num=5)

            for biz in businesses:
                if count >= MAX_SENDS:
                    break
                domain = biz["domain"]
                name   = biz["name"]

                if domain in sent:
                    print(f"  [SKIP] Already contacted: {domain}")
                    continue

                print(f"  [?] Finding email for: {name} ({domain})")
                email = scrape_site_email(domain) or find_email(name, domain)

                if not email:
                    print(f"  [✗] No email found")
                    continue

                print(f"  [✉] Sending to: {email}")
                from omega_outreach_engine import send_outreach
                if send_outreach(email, biz["domain"], city):
                    sent.add(domain)
                    count += 1
                    log["sent"].append(domain)
                    log["total"] = log.get("total", 0) + 1
                    save_log(log)
                    # Sync to omega.db so Telegram shows real count
                    try:
                        import sqlite3, datetime
                        db = sqlite3.connect("/data/data/com.termux/files/home/omega_runtime/db/omega.db")
                        db.execute(
                            "INSERT INTO emails_sent(lead_id,to_email,subject,stage,product_key,provider) VALUES(?,?,?,?,?,?)",
                            (None, email, f"Outreach - {biz['domain']}", "outreach", "lead_runner", "gmail")
                        )
                        db.commit()
                        db.close()
                    except Exception as e:
                        print(f"  [DB SYNC] {e}")
                    print(f"  [✅] Sent #{count}: {email}")
                else:
                    print(f"  [✗] Send failed")

                time.sleep(2)

    print(f"\n{'='*55}")
    print(f"  BATCH COMPLETE — {count} emails sent today")
    print(f"  Total all time: {log['total']}")
    print(f"{'='*55}\n")

if __name__ == "__main__":
    run()
