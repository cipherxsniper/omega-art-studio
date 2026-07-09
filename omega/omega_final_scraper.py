import socket, ssl, re, sqlite3, time, urllib.request, urllib.parse, json

BUSINESSES = [
    ('hvac', ['atlanta','dallas','houston','charlotte','phoenix']),
    ('roofing', ['atlanta','dallas','houston','denver','nashville']),
    ('dental', ['atlanta','dallas','houston','charlotte','miami']),
    ('plumbing', ['atlanta','dallas','phoenix','denver','tampa']),
    ('lawfirm', ['atlanta','dallas','charlotte','nashville','miami']),
]

def get_cert_info(domain):
    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.socket(), server_hostname=domain) as s:
            s.settimeout(5)
            s.connect((domain, 443))
            cert = s.getpeercert()
        org = ''
        for field in cert.get('subject', []):
            for k, v in field:
                if k == 'organizationName':
                    org = v
        emails = []
        san = cert.get('subjectAltName', [])
        return org, emails
    except:
        return '', []

def fetch_whois_email(domain):
    try:
        req = urllib.request.Request(
            f'https://www.whois.com/whois/{domain}',
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode('utf-8', errors='ignore')
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}', html)
        bad = ['whois','example','domain','noreply','privacy','protect']
        return [e for e in emails if not any(b in e.lower() for b in bad)]
    except:
        return []

def discover_domains(category, city):
    found = []
    patterns = [
        f'{category}{city}',
        f'{city}{category}',
        f'{category}-{city}',
        f'{city}-{category}',
        f'best{category}{city}',
        f'{category}pro{city}',
        f'{city}{category}pro',
        f'{category}expert{city}',
    ]
    tlds = ['.com', '.net', '.biz', '.co']
    for pattern in patterns:
        for tld in tlds:
            domain = pattern.lower().replace(' ','') + tld
            try:
                socket.getaddrinfo(domain, None)
                found.append(domain)
            except:
                pass
    return found[:10]

def scrape_contact(domain):
    for scheme in ['https', 'http']:
        for path in ['/contact', '/contact-us', '/about', '']:
            try:
                req = urllib.request.Request(
                    f'{scheme}://{domain}{path}',
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                with urllib.request.urlopen(req, timeout=8) as r:
                    html = r.read().decode('utf-8', errors='ignore')
                emails = re.findall(
                    r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4})',
                    html)
                if not emails:
                    emails = re.findall(
                        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}',
                        html)
                bad = ['noreply','example','domain','test','png','jpg','woff']
                clean = [e for e in emails if not any(b in e for b in bad)]
                if clean:
                    org, _ = get_cert_info(domain)
                    return clean[0], org
            except:
                pass
    return None, ''

conn = sqlite3.connect('/data/data/com.termux/files/home/omega_runtime/db/omega.db')
c = conn.cursor()
found = 0

for category, cities in BUSINESSES:
    for city in cities:
        print(f'Discovering: {category} {city}')
        domains = discover_domains(category, city)
        print(f'  {len(domains)} domains resolve')
        for domain in domains:
            email, org = scrape_contact(domain)
            if email:
                name = org if org else domain.split('.')[0].title()
                c.execute('''INSERT OR IGNORE INTO leads
                    (email,name,category,website,score,status,stage,source)
                    VALUES(?,?,?,?,88,"new",0,"dns_discovery")''',
                    (email, name, f'{category} {city}',
                     f'https://{domain}'))
                if c.rowcount > 0:
                    found += 1
                    print(f'  + {email} | {name}')
                conn.commit()
            time.sleep(0.5)
        time.sleep(1)

print(f'\nTotal: {found}')
c.execute('SELECT COUNT(*) FROM leads WHERE status="new"')
print(f'Ready to pitch: {c.fetchone()[0]}')
conn.close()
