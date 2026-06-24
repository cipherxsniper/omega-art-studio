from omega_db_kernel_v1 import OmegaTransaction, fetch_all

def validate():
    with OmegaTransaction() as cur:
        return fetch_all(cur, "SELECT * FROM ledger_postings")
