import urllib.request as ur
import urllib.parse as up
import re
import sqlite3
import time

def get_business_email(website):
    for path in ['', '/contact', '/contact-us', '/about', '/about-us']:
        try:
            url = website.rstrip('/') + path
            req = ur.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36'
            })
            with ur.urlopen(req, timeout=6) as r:
                html = r.read().decode('utf-8', errors='ignore')
            emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}', html)
            bad = ['noreply','example','domain','test','png','jpg','woff','sentry']
            real = [e for e in emails if not any(b in e.lower() for b in bad)]
            if real:
                return real[0]
        except:
            pass
        time.sleep(0.5)
    return None

SEARCHES = [
    'HVAC contractor Atlanta GA',
    'dental office Atlanta GA',
    'law firm Atlanta GA',
    'roofing contractor Atlanta GA',
    'plumber Atlanta GA',
    'HVAC contractor Dallas TX',
    'dental office Houston TX',
    'law firm Charlotte NC',
]

conn = sqlite3.connect('/data/data/com.termux/files/home/omega_runtime/db/omega.db')
c = conn.cursor()
found = 0

for search in SEARCHES:
    print(f'Searching: {search}')
    try:
        q = up.urlencode({'q': search, 'tbm': 'lcl'})
        req = ur.Request(
            f'https://www.google.com/search?{q}',
            headers={'User-Agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/91.0'}
        )
        with ur.urlopen(req, timeout=10) as r:
            html = r.read().decode('utf-8', errors='ignore')
        websites = re.findall(r'https?://(?!google|gstatic|youtube|facebook|yelp|yellowpages)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s"<>]*)?', html)
        websites = list(set(w.split('?')[0] for w in websites))[:8]
        print(f'  Found {len(websites)} sites to check')
        for site in websites:
            email = get_business_email(site)
            if email:
                domain = site.split('/')[2].replace('www.','')
                name = domain.split('.')[0].title()
                c.execute('INSERT OR IGNORE INTO leads(email,name,category,website,score,status,stage,source) VALUES(?,?,?,?,80,"new",0,"scraper")',
                    (email, name, search, site))
                if c.rowcount > 0:
                    found += 1
                    print(f'  + {email}')
                conn.commit()
            time.sleep(1)
    except Exception as e:
        print(f'  Error: {e}')
    time.sleep(3)

print(f'\nTotal new leads: {found}')
conn.close()
