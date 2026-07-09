from omega_db_kernel_v1 import OmegaTransaction, fetch_all

def run():
    with OmegaTransaction() as cur:
        events = fetch_all(cur, "SELECT * FROM omega_events")
        return events


if __name__ == "__main__":
    print("REPLAY OK")
    print(run())
