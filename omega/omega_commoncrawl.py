import urllib.request as ur
import urllib.parse as up
import re, sqlite3, time, json, socket

def mx_verify(domain):
    try:
        socket.getaddrinfo(domain, None)
        return True
    except:
        return False

def search_commoncrawl(query):
    try:
        q = up.urlencode({'url': f'*.com', 'output': 'json',
                         'fl': 'url', 'filter': f'~{query}',
                         'limit': '20'})
        req = ur.Request(
            f'https://index.commoncrawl.org/CC-MAIN-2024-10-index?{q}',
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with ur.urlopen(req, timeout=15) as r:
            lines = r.read().decode('utf-8', errors='ignore').strip().split('\n')
        urls = []
        for line in lines:
            try:
                data = json.loads(line)
                urls.append('https://' + data['url'].split('/')[0])
            except:
                pass
        return list(set(urls))[:10]
    except Exception as e:
        print(f'  CC error: {e}')
        return []

def get_email(url):
    for path in ['/contact', '/contact-us', '/about', '']:
        try:
            req = ur.Request(url.rstrip('/')+path,
                headers={'User-Agent': 'Mozilla/5.0'})
            with ur.urlopen(req, timeout=8) as r:
                html = r.read().decode('utf-8', errors='ignore')
            emails = re.findall(
                r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}', html)
            bad = ['noreply','example','domain','test','png','jpg']
            clean = [e for e in emails
                    if not any(b in e.lower() for b in bad)]
            if clean:
                return clean[0]
        except:
            pass
    return None

QUERIES = [
    'hvac+atlanta', 'dental+atlanta', 'roofing+dallas',
    'plumbing+houston', 'lawfirm+charlotte', 'hvac+phoenix',
]

conn = sqlite3.connect(
    '/data/data/com.termux/files/home/omega_runtime/db/omega.db')
c = conn.cursor()
found = 0

for query in QUERIES:
    print(f'Searching Common Crawl: {query}')
    urls = search_commoncrawl(query)
    print(f'  {len(urls)} sites found')
    for url in urls:
        try:
            domain = url.split('/')[2].replace('www.','')
            if not mx_verify(domain):
                continue
            email = get_email(url)
            if email:
                name = domain.split('.')[0].title()
                c.execute('''INSERT OR IGNORE INTO leads
                    (email,name,category,website,score,status,stage,source)
                    VALUES(?,?,?,?,80,"new",0,"commoncrawl")''',
                    (email, name, query, url))
                if c.rowcount > 0:
                    found += 1
                    print(f'  + {email}')
                conn.commit()
        except:
            pass
        time.sleep(1)
    time.sleep(2)

print(f'\nTotal: {found}')
conn.close()
# Telegram notification
import os
from dotenv import load_dotenv
load_dotenv()
token = os.getenv('TELEGRAM_BOT_TOKEN')
chat = os.getenv('TELEGRAM_ADMIN_IDS','').split(',')[0]
if token and chat and found > 0:
    msg = up.urlencode({'chat_id': chat, 'text': f'Lead engine found {found} new leads'})
    ur.urlopen(f'https://api.telegram.org/bot{token}/sendMessage?{msg}')
