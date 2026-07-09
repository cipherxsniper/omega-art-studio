import urllib.request as ur
import urllib.parse as up
import re, sqlite3, time, socket

def fetch(url, via_tor=False):
    try:
        if via_tor:
            import socks
            s = socks.socksocket()
            s.set_proxy(socks.SOCKS5, "127.0.0.1", 9050)
        req = ur.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html'
        })
        with ur.urlopen(req, timeout=10) as r:
            return r.read().decode('utf-8', errors='ignore')
    except:
        return ''

def mx_valid(domain):
    try:
        socket.getaddrinfo(domain, None)
        return True
    except:
        return False

def find_email(html):
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}', html)
    bad = ['noreply','example','domain','test','png','jpg','woff','sentry','@2x']
    return [e for e in emails if not any(b in e.lower() for b in bad)]

SEARCHES = [
    'HVAC company Atlanta site:*.com',
    'roofing contractor Dallas site:*.com', 
    'dental clinic Houston site:*.com',
    'law firm Charlotte site:*.com',
    'plumber Phoenix site:*.com',
    'accounting firm Nashville site:*.com',
]

conn = sqlite3.connect('/data/data/com.termux/files/home/omega_runtime/db/omega.db')
c = conn.cursor()
found = 0

for search in SEARCHES:
    q = up.urlencode({'q': search})
    html = fetch(f'https://html.duckduckgo.com/html/?{q}')
    urls = re.findall(r'class="result__url"[^>]*>([^<]+)<', html)
    urls = ['https://'+u.strip() for u in urls if u.strip()]
    print(f'{search[:40]}: {len(urls)} sites')
    for url in urls[:5]:
        if any(x in url for x in ['yelp','facebook','google','angi','thumbtack','bbb']):
            continue
        domain = url.split('/')[2].replace('www.','')
        if not mx_valid(domain):
            continue
        for path in ['/contact','/about','']:
            page = fetch(url.rstrip('/')+path)
            emails = find_email(page)
            for email in emails[:1]:
                c.execute('INSERT OR IGNORE INTO leads(email,name,category,website,score,status,stage,source) VALUES(?,?,?,?,80,"new",0,"scraped")',
                    (email, domain.split('.')[0].title(), search, url))
                if c.rowcount > 0:
                    found += 1
                    print(f'  + {email}')
                conn.commit()
            if emails:
                break
        time.sleep(1)
    time.sleep(2)

print(f'Total: {found}')
conn.close()
