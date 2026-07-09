
CREATE TABLE IF NOT EXISTS virtual_cards (
    id UUID PRIMARY KEY,
    wallet_id UUID NOT NULL,
    card_token TEXT UNIQUE NOT NULL,
    spendable_limit NUMERIC(20,2) NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS card_transactions (
    id UUID PRIMARY KEY,
    card_token TEXT NOT NULL,
    wallet_id UUID NOT NULL,
    amount NUMERIC(20,2) NOT NULL,
    merchant TEXT,
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT now(),
    idempotency_key TEXT UNIQUE
);

