from core.omega_ledger import ledger

SYSTEM = ledger.create_account("SYSTEM")
REVENUE = ledger.create_account("REVENUE")

print("SYSTEM:", SYSTEM)
print("REVENUE:", REVENUE)
