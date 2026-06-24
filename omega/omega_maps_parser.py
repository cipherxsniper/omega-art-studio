import socks, socket, urllib.request, re, urllib.parse, json

socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 9050)
socket.socket = socks.socksocket

def search_maps(query):
    q = urllib.parse.quote(query)
    req = urllib.request.Request(
        f"https://www.google.com/maps/search/{q}",
        headers={
            "User-Agent": "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        html = r.read().decode("utf-8", errors="replace")
    
    # Extract business names and websites from Maps data
    names = re.findall(r'"([^"]{3,50})",null,null,null,null,\["([^"]+\.com)', html)
    websites = re.findall(r'https?://(?!google|gstatic|maps)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s"\\]*)?', html)
    phones = re.findall(r'\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}', html)
    
    # Clean websites
    clean_sites = list(set([
        'https://' + w.split('/')[0] if not w.startswith('http') else w.split('?')[0]
        for w in websites
        if not any(x in w for x in ['google','gstatic','schema','w3.org','apple'])
    ]))[:10]
    
    return clean_sites, phones[:5]

def get_email_from_site(url):
    try:
        req = urllib.request.Request(url + '/contact', headers={
            "User-Agent": "Mozilla/5.0"
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode('utf-8', errors='ignore')
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}', html)
        bad = ['noreply','example','domain','test','png','jpg']
        return [e for e in emails if not any(b in e for b in bad)]
    except:
        return []

import sqlite3, time
conn = sqlite3.connect('/data/data/com.termux/files/home/omega_runtime/db/omega.db')
c = conn.cursor()
found = 0

SEARCHES = [
    'HVAC company Atlanta GA',
    'roofing contractor Dallas TX', 
    'dental office Houston TX',
    'law firm Charlotte NC',
    'plumber Phoenix AZ',
]

for search in SEARCHES:
    print(f'Searching: {search}')
    try:
        sites, phones = search_maps(search)
        print(f'  {len(sites)} sites found')
        for site in sites:
            emails = get_email_from_site(site)
            for email in emails[:1]:
                domain = site.split('/')[2].replace('www.','')
                name = domain.split('.')[0].title()
                c.execute('INSERT OR IGNORE INTO leads(email,name,category,website,score,status,stage,source) VALUES(?,?,?,?,85,"new",0,"maps_scraper")',
                    (email, name, search, site))
                if c.rowcount > 0:
                    found += 1
                    print(f'  + {email}')
                conn.commit()
            time.sleep(1)
    except Exception as e:
        print(f'  Error: {e}')
    time.sleep(3)

print(f'\nTotal: {found}')
conn.close()
