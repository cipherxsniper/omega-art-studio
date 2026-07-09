import urllib.request as ur
import urllib.parse as up
import re, sqlite3, time, socket, json

def fetch(url):
    try:
        req = ur.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        with ur.urlopen(req, timeout=12) as r:
            raw = r.read()
            try:
                return raw.decode('utf-8')
            except:
                return raw.decode('latin-1', errors='ignore')
    except Exception as e:
        return ''

def extract_emails(html):
    patterns = [
        r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4})',
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}',
    ]
    emails = []
    for p in patterns:
        emails.extend(re.findall(p, html))
    bad = ['noreply','example','domain','test','png','jpg','woff',
           'sentry','privacy','legal','press','media','support']
    owner = ['owner','ceo','founder','president','director','manager',
             'contact','hello','team','info']
    clean = [e.lower() for e in emails
             if not any(b in e.lower() for b in bad)]
    prioritized = [e for e in clean
                   if any(o in e.lower() for o in owner)]
    return (prioritized + [e for e in clean if e not in prioritized])[:3]

def mx_valid(domain):
    try:
        socket.getaddrinfo(domain, None)
        return True
    except:
        return False

def scrape_bbb(category, city, state):
    url = f'https://www.bbb.org/search?find_text={up.quote(category)}&find_loc={up.quote(city+","+state)}'
    html = fetch(url)
    urls = re.findall(r'href="(https://www\.bbb\.org/us/[^"]+)"', html)
    return list(set(urls))[:10]

def scrape_bbb_listing(url):
    html = fetch(url)
    name_m = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
    name = name_m.group(1).strip() if name_m else ''
    website_m = re.search(r'href="(https?://(?!bbb\.org)[^"]+)"[^>]*>Website<', html)
    website = website_m.group(1) if website_m else ''
    phone_m = re.search(r'(\(\d{3}\)\s*\d{3}-\d{4})', html)
    phone = phone_m.group(1) if phone_m else ''
    return name, website, phone

TARGETS = [
    ('HVAC', 'Atlanta', 'GA'),
    ('Roofing', 'Dallas', 'TX'),
    ('Dental', 'Houston', 'TX'),
    ('Law Firm', 'Charlotte', 'NC'),
    ('Plumbing', 'Phoenix', 'AZ'),
    ('Accounting', 'Nashville', 'TN'),
    ('HVAC', 'Miami', 'FL'),
    ('Roofing', 'Denver', 'CO'),
]

conn = sqlite3.connect(
    '/data/data/com.termux/files/home/omega_runtime/db/omega.db')
c = conn.cursor()
found = 0

for cat, city, state in TARGETS:
    print(f'Scraping BBB: {cat} in {city}, {state}')
    listings = scrape_bbb(cat, city, state)
    print(f'  {len(listings)} listings found')

    for listing_url in listings:
        name, website, phone = scrape_bbb_listing(listing_url)
        if not website:
            continue
        domain = website.split('/')[2].replace('www.', '')
        if not mx_valid(domain):
            continue
        email = None
        for path in ['/contact', '/contact-us', '/about', '/team', '']:
            page = fetch(website.rstrip('/') + path)
            emails = extract_emails(page)
            if emails:
                email = emails[0]
                break
            time.sleep(0.5)
        if email:
            c.execute('''INSERT OR IGNORE INTO leads
                (email,name,category,website,score,status,stage,source)
                VALUES(?,?,?,?,85,"new",0,"bbb_scraper")''',
                (email, name or domain.split('.')[0].title(),
                 f'{cat} {city}', website))
            if c.rowcount > 0:
                found += 1
                print(f'  + {email} | {name}')
            conn.commit()
        time.sleep(1.5)
    time.sleep(3)

print(f'\nTotal verified leads: {found}')
conn.close()
