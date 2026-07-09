import sqlite3
conn = sqlite3.connect('/data/data/com.termux/files/home/omega_runtime/db/omega.db')
c = conn.cursor()
leads = [
    ('real@actualbusiness.com', 'Real Business Name', 'hvac company', 'https://theirwebsite.com'),
]
for email, name, cat, site in leads:
    c.execute('INSERT OR IGNORE INTO leads(email,name,category,website,score,status,stage,source) VALUES(?,?,?,?,85,"new",0,"manual")', (email,name,cat,site))
conn.commit()
print('Added:', c.rowcount)
