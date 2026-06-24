import urllib.request as ur
import urllib.parse as up
import re
import sqlite3
import time
import random

AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
]

TARGETS = [
    'https://www.manta.com/mb_47_A108E000_0/hvac/georgia/atlanta',
    'https://www.manta.com/mb_47_A103H000_0/plumbing/georgia/atlanta',
    'https://www.manta.com/mb_47_A104A000_0/roofing/georgia/atlanta',
    'https://www.manta.com/mb_47_A106F000_0/dental/georgia/atlanta',
]

def extract_emails(html):
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}', html)
    bad = ['noreply','example','domain','test','png','jpg','woff','manta','sentry']
    return list(set(e.lower() for e in emails if not any(b in e.lower() for b in bad)))

def fetch(url):
    try:
        req = ur.Request(url, headers={
            'User-Agent': random.choice(AGENTS),
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        with ur.urlopen(req, timeout=10) as r:
            return r.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f'  Error: {e}')
        return ''

conn = sqlite3.connect('/data/data/com.termux/files/home/omega_runtime/db/omega.db')
c = conn.cursor()
found = 0

for url in TARGETS:
    print(f'Scraping: {url}')
    html = fetch(url)
    links = re.findall(r'href="(https?://[^"]+)"', html)
    biz_links = [l for l in links if 'manta.com/c/' in l][:10]
    print(f'  Found {len(biz_links)} businesses')
    for link in biz_links:
        biz_html = fetch(link)
        emails = extract_emails(biz_html)
        name_match = re.search(r'<h1[^>]*>([^<]+)</h1>', biz_html)
        name = name_match.group(1).strip() if name_match else link.split('/')[-1].title()
        for email in emails[:1]:
            c.execute('INSERT OR IGNORE INTO leads(email,name,category,website,score,status,stage,source) VALUES(?,?,?,?,80,"new",0,"scraper")',
                (email, name, url.split('/')[-1], link))
            if c.rowcount > 0:
                found += 1
                print(f'  + {email} ({name})')
        conn.commit()
        time.sleep(random.uniform(1, 2))
    time.sleep(3)

print(f'\nTotal new leads: {found}')
conn.close()
