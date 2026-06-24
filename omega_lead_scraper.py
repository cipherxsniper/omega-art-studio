import urllib.request as ur
import urllib.parse as up
import re
import sqlite3
import time

def find_emails_on_page(url):
    try:
        req = ur.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with ur.urlopen(req, timeout=10) as r:
            html = r.read().decode('utf-8', errors='ignore')
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html)
        # Filter out generic emails
        real = [e for e in emails if not any(x in e.lower() for x in ['noreply','example','domain','test'])]
        return list(set(real))
    except Exception as e:
        return []

def search_google(query):
    try:
        q = up.urlencode({'q': query})
        url = f'https://www.google.com/search?{q}&num=10'
        req = ur.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with ur.urlopen(req, timeout=10) as r:
            html = r.read().decode('utf-8', errors='ignore')
        urls = re.findall(r'href="(https?://(?!google)[^"]+)"', html)
        return [u for u in urls if 'google' not in u][:5]
    except Exception as e:
        return []

categories = [
    'hvac company atlanta',
    'dental clinic atlanta', 
    'law firm atlanta',
    'roofing company atlanta',
    'plumbing company atlanta',
]

conn = sqlite3.connect('/data/data/com.termux/files/home/omega_runtime/db/omega.db')
c = conn.cursor()
found = 0

for cat in categories:
    print(f'Searching: {cat}')
    urls = search_google(cat)
    for url in urls:
        emails = find_emails_on_page(url)
        for email in emails:
            domain = url.split('/')[2].replace('www.','')
            name = domain.split('.')[0].title()
            try:
                c.execute('INSERT OR IGNORE INTO leads(email,name,category,website,score,status,stage,source) VALUES(?,?,?,?,80,"new",0,"scraper")',
                    (email, name, cat, url))
                if c.rowcount > 0:
                    found += 1
                    print(f'  Found: {email}')
            except Exception:
                pass
        time.sleep(2)
    conn.commit()
    time.sleep(3)

print(f'Total found: {found}')
conn.close()
