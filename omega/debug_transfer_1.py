import sqlite3

conn = sqlite3.connect("omega_ledger.db")

print("\nACCOUNTS:")
for row in conn.execute("SELECT * FROM accounts"):
    print(row)

print("\nTRANSACTIONS:")
for row in conn.execute("SELECT * FROM transactions"):
    print(row)

print("\nENTRIES:")
for row in conn.execute("SELECT * FROM entries"):
    print(row)
