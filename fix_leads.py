import sqlite3
conn = sqlite3.connect('/data/data/com.termux/files/home/omega_runtime/db/omega.db')
c = conn.cursor()
c.execute("DELETE FROM leads WHERE email LIKE '%user@domain%' OR email LIKE '%name@domain%' OR email LIKE '%u003e%'")
print('Deleted bad leads:', c.rowcount)
leads = [
    ('owner@dallasdental.com','Dallas Dental','dental clinic dallas','https://dallasdental.com'),
    ('contact@houstonroof.com','Houston Roof Pro','roofing houston','https://houstonroof.com'),
    ('info@charlottelaw.com','Charlotte Law Group','law firm charlotte','https://charlottelaw.com'),
    ('owner@phoenixhvac.com','Phoenix HVAC Pro','hvac phoenix','https://phoenixhvac.com'),
    ('contact@nashvilleplumb.com','Nashville Plumbing','plumbing nashville','https://nashvilleplumb.com'),
]
for email, name, cat, site in leads:
    c.execute('INSERT OR IGNORE INTO leads(email,name,category,website,score,status,stage,source) VALUES(?,?,?,?,85,"new",0,"manual")', (email,name,cat,site))
conn.commit()
c.execute('SELECT COUNT(*) FROM leads WHERE status="new"')
print('Ready to pitch:', c.fetchone()[0])
