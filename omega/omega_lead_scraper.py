import urllib.request as ur
import urllib.parse as up
import re
import sqlite3
import time
import json

CATEGORIES = [
    ('hvac', 'atlanta'),
    ('dental clinic', 'atlanta'),
    ('law firm', 'atlanta'),
    ('roofing', 'dallas'),
    ('plumbing', 'houston'),
]

def scrape_business_site(url):
    try:
        req = ur.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36',
            'Accept': 'text/html'
        })
        with ur.urlopen(req, timeout=8) as r:
            html = r.read().decode('utf-8', errors='ignore')
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}', html)
        bad = ['noreply','example','domain','test','sentry','png','jpg','svg','woff']
        return list(set(e.lower() for e in emails if not any(b in e.lower() for b in bad)))
    except:
        return []

def search_bing(query):
    try:
        q = up.urlencode({'q': query, 'count': '10'})
        req = ur.Request(
            f'https://www.bing.com/search?{q}',
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        with ur.urlopen(req, timeout=10) as r:
            html = r.read().decode('utf-8', errors='ignore')
        urls = re.findall(r'(https?://[^<]+)', html)
        clean = []
        for u in urls:
            if not any(x in u for x in ['bing.com','microsoft','linkedin','facebook','yelp','yellowpages']):
                clean.append(u.split('?')[0])
        return clean[:6]
    except Exception as e:
        print(f'Search error: {e}')
        return []

conn = sqlite3.connect('/data/data/com.termux/files/home/omega_runtime/db/omega.db')
c = conn.cursor()
found = 0

for cat, city in CATEGORIES:
    query = f'{cat} company {city} contact email'
    print(f'Searching: {query}')
    urls = search_bing(query)
    print(f'  Found {len(urls)} sites')
    for url in urls:
        emails = scrape_business_site(url)
        for email in emails:
            domain = url.split('/')[2].replace('www.','')
            name = domain.split('.')[0].title()
            try:
                c.execute('INSERT OR IGNORE INTO leads(email,name,category,website,score,status,stage,source) VALUES(?,?,?,?,80,"new",0,"scraper")',
                    (email, name, f'{cat} {city}', url))
                if c.rowcount > 0:
                    found += 1
                    print(f'  + {email} ({name})')
            except:
                pass
        conn.commit()
        time.sleep(1)
    time.sleep(2)

print(f'\nTotal new leads found: {found}')
conn.close()
