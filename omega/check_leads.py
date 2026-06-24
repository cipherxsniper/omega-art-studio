import sqlite3
conn = sqlite3.connect('/data/data/com.termux/files/home/omega_runtime/db/omega.db')
c = conn.cursor()
c.execute('SELECT status, COUNT(*) FROM leads GROUP BY status ORDER BY COUNT(*) DESC')
for r in c.fetchall(): print(r)
