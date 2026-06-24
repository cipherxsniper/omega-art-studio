import socket
import urllib.request as ur
import urllib.parse as up
import re
import sqlite3
import time
import random

# Route through Tor SOCKS5
def tor_opener():
    import socks, socket
    socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 9050)
    socket.socket = socks.socksocket
    return ur.build_opener()

AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0',
]

def fetch(url, use_tor=True):
    try:
        opener = tor_opener() if use_tor else ur.build_opener()
        req = ur.Request(url, headers={
            'User-Agent': random.choice(AGENTS),
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        with opener.open(req, timeout=15) as r:
            return r.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return ''

def extract_emails(html):
    raw = re.findall(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}', html)
    bad = ['noreply','example','domain','test','png','jpg',
           'woff','sentry','privacy','legal']
    good = ['owner','ceo','founder','president','director',
            'manager','contact','hello','info','admin']
    clean = [e.lower() for e in raw
             if not any(b in e.lower() for b in bad)]
    priority = [e for e in clean if any(g in e for g in good)]
    rest = [e for e in clean if e not in priority]
    return (priority + rest)[:2]

def mx_valid(domain):
    try:
        socket.getaddrinfo(domain, None)
        return True
    except:
        return False

def get_tor_ip():
    try:
        opener = tor_opener()
        req = ur.Request('https://httpbin.org/ip',
            headers={'User-Agent': random.choice(AGENTS)})
        with opener.open(req, timeout=10) as r:
            import json
            return json.loads(r.read()).get('origin', 'unknown')
    except:
        return 'unknown'

QUERIES = [
    'HVAC contractor Atlanta Georgia',
    'roofing company Dallas Texas',
    'dental practice Houston Texas',
    'law firm Charlotte North Carolina',
    'plumbing company Phoenix Arizona',
    'accounting firm Nashville Tennessee',
    'med spa Atlanta Georgia',
    'auto repair Dallas Texas',
    'landscaping Houston Texas',
    'insurance agency Charlotte North Carolina',
]

print(f'Tor IP: {get_tor_ip()}')

conn = sqlite3.connect(
    '/data/data/com.termux/files/home/omega_runtime/db/omega.db')
c = conn.cursor()
found = 0

for query in QUERIES:
    print(f'\nSearching: {query}')
    q = up.urlencode({'q': query})
    html = fetch(f'https://html.duckduckgo.com/html/?{q}')
    if not html:
        print('  No response — Tor may need restart')
        continue

    urls = re.findall(
        r'<a class="result__url"[^>]*href="([^"]+)"', html)
    if not urls:
        urls = re.findall(r'uddg=([^&"]+)', html)
        urls = [up.unquote(u) for u in urls]

    urls = [u for u in urls if not any(x in u for x in
        ['duckduckgo','yelp','facebook','google','angi',
         'thumbtack','bbb.org','linkedin','yellowpages'])][:6]

    print(f'  {len(urls)} business sites to check')

    for url in urls:
        if not url.startswith('http'):
            url = 'https://' + url
        try:
            domain = url.split('/')[2].replace('www.', '')
        except:
            continue
        if not mx_valid(domain):
            continue

        email = None
        for path in ['/contact', '/contact-us', '/about',
                     '/team', '/staff', '']:
            page = fetch(url.rstrip('/') + path)
            emails = extract_emails(page)
            if emails:
                email = emails[0]
                break
            time.sleep(0.5)

        if email:
            name = domain.split('.')[0].replace('-', ' ').title()
            c.execute('''INSERT OR IGNORE INTO leads
                (email,name,category,website,score,
                 status,stage,source)
                VALUES(?,?,?,?,82,"new",0,"omega_scraper")''',
                (email, name, query, url))
            if c.rowcount > 0:
                found += 1
                print(f'  + {email} | {name}')
            conn.commit()

        time.sleep(random.uniform(1.5, 3.0))

    time.sleep(random.uniform(3, 5))

print(f'\nTotal verified leads: {found}')
c.execute('SELECT COUNT(*) FROM leads WHERE status="new"')
print(f'Total ready to pitch: {c.fetchone()[0]}')
conn.close()
