import socks, socket, urllib.request, re, sqlite3, time, random

socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 9050)
socket.socket = socks.socksocket

AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Firefox/119.0',
]

def fetch(url):
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': random.choice(AGENTS),
            'Accept': 'text/html',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        with urllib.request.urlopen(req, timeout=12) as r:
            return r.read().decode('utf-8', errors='ignore')
    except:
        return ''

def extract_emails(html):
    found = set()
    # mailto links first - highest quality
    mailto = re.findall(r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4})', html)
    found.update(mailto)
    # Raw emails second
    raw = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}', html)
    found.update(raw)
    bad = ['noreply','example','domain','test','png','jpg','woff','sentry','2x','webp']
    return [e.lower() for e in found if not any(b in e.lower() for b in bad)]

def extract_business_urls(html):
    urls = re.findall(r'https?://(?!(?:www\.)?(?:google|facebook|yelp|angi|thumbtack|bbb|linkedin|twitter|instagram|youtube))[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s"\'<>]*)?', html)
    return list(set(u.split('?')[0].rstrip('/') for u in urls))[:15]

def find_email_on_site(base_url):
    paths = ['/contact','/contact-us','/about','/about-us','/team','/reach-us','']
    for path in paths:
        html = fetch(base_url + path)
        emails = extract_emails(html)
        if emails:
            return emails[0], html
        time.sleep(0.5)
    return None, ''

def extract_business_name(html, url):
    patterns = [
        r'<title>([^|<-]+)',
        r'<h1[^>]*>([^<]{3,60})</h1>',
        r'"name"\s*:\s*"([^"]{3,60})"',
    ]
    for p in patterns:
        m = re.search(p, html)
        if m:
            return m.group(1).strip()[:50]
    return url.split('/')[2].replace('www.','').split('.')[0].title()

SEARCHES = [
    ('hvac+company+Atlanta+GA', 'hvac atlanta'),
    ('roofing+contractor+Dallas+TX', 'roofing dallas'),
    ('dental+office+Houston+TX', 'dental houston'),
    ('law+firm+Charlotte+NC', 'law firm charlotte'),
    ('plumber+Phoenix+AZ', 'plumbing phoenix'),
    ('accounting+firm+Nashville+TN', 'accounting nashville'),
    ('med+spa+Atlanta+GA', 'med spa atlanta'),
    ('auto+repair+Denver+CO', 'auto repair denver'),
]

conn = sqlite3.connect('/data/data/com.termux/files/home/omega_runtime/db/omega.db')
c = conn.cursor()
found = 0

for query, category in SEARCHES:
    print(f'Searching: {category}')
    html = fetch(f'https://html.duckduckgo.com/html/?q={query}')
    if not html:
        print('  Blocked')
        continue
    urls = extract_business_urls(html)
    print(f'  {len(urls)} sites discovered')
    for url in urls:
        if not url.startswith('http'):
            continue
        email, page_html = find_email_on_site(url)
        if email:
            name = extract_business_name(page_html, url)
            c.execute('''INSERT OR IGNORE INTO leads
                (email,name,category,website,score,status,stage,source)
                VALUES(?,?,?,?,85,"new",0,"evo_scraper")''',
                (email, name, category, url))
            if c.rowcount > 0:
                found += 1
                print(f'  + {email} | {name}')
            conn.commit()
        time.sleep(random.uniform(1, 2))
    time.sleep(random.uniform(2, 4))

print(f'\nTotal new leads: {found}')
c.execute('SELECT COUNT(*) FROM leads WHERE status="new"')
print(f'Ready to pitch: {c.fetchone()[0]}')
conn.close()
