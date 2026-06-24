import urllib.request as ur
import urllib.parse as up
import re
import sqlite3
import time
import json
import socket

BUSINESS_TYPES = ['hvac','dental','roofing','plumbing','law','accounting']
CITIES = ['atlanta','dallas','houston','charlotte','phoenix']

def check_common_emails(domain):
    prefixes = ['owner','contact','info','hello','admin']
    found = []
    for prefix in prefixes:
        email = f'{prefix}@{domain}'
        try:
            socket.getaddrinfo(domain, None)
            found.append(email)
            break
        except:
            pass
    return found

def search_duckduckgo(query):
    try:
        q = up.urlencode({'q': query, 'format': 'json', 'no_html': '1', 'skip_disambig': '1'})
        req = ur.Request(
            f'https://api.duckduckgo.com/?{q}',
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with ur.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        results = []
        for r in data.get('Results', []):
            url = r.get('FirstURL', '')
            if url: results.append(url)
        return results[:5]
    except Exception as e:
        return []

def scrape_contact_page(url):
    for path in ['/contact', '/contact-us', '/about', '']:
        try:
            full = url.rstrip('/') + path
            req = ur.Request(full, headers={'User-Agent': 'Mozilla/5.0'})
            with ur.urlopen(req, timeout=8) as r:
                html = r.read().decode('utf-8', errors='ignore')
            emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}', html)
            bad = ['noreply','example','domain','test','png','jpg','woff']
            clean = [e for e in emails if not any(b in e.lower() for b in bad)]
            if clean:
                return clean[0], html
        except:
            pass
    return None, ''

def extract_business_name(html):
    for pattern in [r'<title>([^<|]+)', r'<h1[^>]*>([^<]+)</h1>']:
        m = re.search(pattern, html)
        if m:
            return m.group(1).strip()[:50]
    return 'Unknown'

conn = sqlite3.connect('/data/data/com.termux/files/home/omega_runtime/db/omega.db')
c = conn.cursor()
found = 0

for btype in BUSINESS_TYPES:
    for city in CITIES[:2]:
        query = f'{btype} business {city}'
        print(f'Searching: {query}')
        urls = search_duckduckgo(query)
        for url in urls:
            if any(x in url for x in ['yelp','facebook','linkedin','google','yellowpages']):
                continue
            email, html = scrape_contact_page(url)
            if not email:
                domain = url.split('/')[2].replace('www.','')
                emails = check_common_emails(domain)
                email = emails[0] if emails else None
            if email:
                name = extract_business_name(html) if html else url.split('/')[2]
                c.execute('INSERT OR IGNORE INTO leads(email,name,category,website,score,status,stage,source) VALUES(?,?,?,?,75,"new",0,"dns_scraper")',
                    (email, name, f'{btype} {city}', url))
                if c.rowcount > 0:
                    found += 1
                    print(f'  + {email} ({name})')
                conn.commit()
            time.sleep(1)
        time.sleep(2)

print(f'\nTotal: {found}')
conn.close()
