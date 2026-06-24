import os

files = [
    "api/routes/transactions.py",
    "core/holds.py",
    "core/treasury.py",
    "core/reconciliation.py",
]

print("Manual fix required: SQLAlchemy 2.x requires text() wrapper.")
print("Search pattern:")
print('db.execute("""')

print("\nReplace with:")
print("db.execute(text(\"\"\" ... \"\"\"), params)")
