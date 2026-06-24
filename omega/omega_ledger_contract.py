FORBIDDEN_SQL = [
    "UPDATE accounts SET balance",
    "SET balance =",
]

def validate_sql(query: str):
    q = query.upper()
    for rule in FORBIDDEN_SQL:
        if rule in q:
            raise RuntimeError(f"ILLEGAL LEDGER MUTATION: {rule}")
