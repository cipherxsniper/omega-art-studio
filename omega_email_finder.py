#!/usr/bin/env python3
"""
OMEGA EMAIL FINDER — 3-Layer Owner Email Discovery
Layer 1: SerpAPI Google search for owner email
Layer 2: SMTP RCPT TO pattern verification
Layer 3: Hard reject — never info@ fallback
"""
import re, socket, smtplib, time, logging
import requests

log = logging.getLogger("OmegaEmailFinder")
SERPAPI_KEY = None

EMAIL_PATTERNS = [
    "{first}@{domain}", "{first}.{last}@{domain}",
    "{first}{last}@{domain}", "{first}{l}@{domain}",
    "{f}{last}@{domain}", "{f}.{last}@{domain}",
]
JUNK_PREFIXES = [
    "info","contact","hello","support","admin","office",
    "mail","team","sales","noreply","no-reply","help"
]

def smtp_verify(email, from_email="verify@omegaops.ai"):
    try:
        domain = email.split("@")[1]
        with smtplib.SMTP(domain, 25, timeout=8) as s:
            s.ehlo_or_helo_if_needed()
            s.mail(from_email)
            code, _ = s.rcpt(email)
            return code == 250
    except Exception:
        return False

def _serpapi_find_owner_email(business_name, domain):
    if not SERPAPI_KEY:
        return None
    email_re = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    queries = [
        f'"{business_name}" owner email',
        f'"{business_name}" CEO contact email',
    ]
    for query in queries:
        try:
            r = requests.get(
                "https://serpapi.com/search",
                params={"api_key": SERPAPI_KEY, "engine": "google", "q": query, "num": 5},
                timeout=15,
            )
            for result in r.json().get("organic_results", []):
                snippet = result.get("snippet", "") + result.get("title", "")
                for email in email_re.findall(snippet):
                    local = email.split("@")[0].lower()
                    if local not in JUNK_PREFIXES and domain in email:
                        return email.lower()
            time.sleep(0.5)
        except Exception as e:
            log.warning(f"SerpAPI search failed: {e}")
    return None

def _pattern_verify(owner_name, domain):
    if not owner_name or " " not in owner_name:
        return None
    parts = owner_name.lower().strip().split()
    if len(parts) < 2:
        return None
    first = re.sub(r"[^a-z]", "", parts[0])
    last  = re.sub(r"[^a-z]", "", parts[-1])
    if not first or not last:
        return None
    f, l = first[0], last[0]
    for pattern in EMAIL_PATTERNS:
        email = pattern.format(first=first, last=last, f=f, l=l, domain=domain)
        try:
            if smtp_verify(email):
                return email
        except Exception:
            pass
        time.sleep(0.2)
    return None

def find_owner_email(business_name, domain, owner_name=""):
    email = _serpapi_find_owner_email(business_name, domain)
    if email:
        return email
    if owner_name:
        email = _pattern_verify(owner_name, domain)
        if email:
            return email
    return None
