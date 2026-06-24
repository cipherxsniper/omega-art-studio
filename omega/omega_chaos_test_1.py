import psycopg2
import random
import uuid
import time
import json

DB = "dbname=omega_bank user=omega"

wallets = [
    "8fcaf9c3-24d1-4c4b-ad88-856576b8b6e9",
    "70e8cdae-983c-4392-a97a-4ae06217b303",
    "7597e069-65bc-4b55-b420-a2a2682f53e0"
]

def send(cur):
    from_w = random.choice(wallets)
    to_w = random.choice(wallets)
    amount = random.randint(10, 500)

    payload = json.dumps({
        "amount": str(amount),
        "from_wallet": from_w,
        "to_wallet": to_w
    })

    cur.execute("""
        INSERT INTO settlement_queue (
            id,
            event_type,
            status,
            payload,
            idempotency_key,
            created_at,
            updated_at,
            retry_count
        )
        VALUES (
            gen_random_uuid(),
            'TRANSFER_REQUESTED',
            'PENDING',
            %s::jsonb,
            %s,
            now(),
            now(),
            0
        );
    """, (payload, str(uuid.uuid4())))

def run():
    conn = psycopg2.connect(DB)
    conn.autocommit = True
    cur = conn.cursor()

    for _ in range(200):
        send(cur)
        time.sleep(0.05)

if __name__ == "__main__":
    run()
