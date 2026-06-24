from omega_db_kernel_v1 import OmegaTransaction, fetch_one

def check(key):
    with OmegaTransaction() as cur:
        return fetch_one(
            cur,
            "SELECT 1 FROM omega_events WHERE event_id = %s",
            (key,)
        )
