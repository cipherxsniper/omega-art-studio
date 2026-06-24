
import sqlite3
import uuid
from datetime import datetime, timezone
import json

DATABASE_FILE = "omega_cloud.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row # This allows accessing columns by name
    return conn

def migrate_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Table: omega_accounts (for formal user/owner management)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS omega_accounts (
            account_id TEXT PRIMARY KEY,
            account_name TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)

    # Table: omega_storage_metadata
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS omega_storage_metadata (
            object_id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL,
            object_name TEXT NOT NULL,
            content_type TEXT,
            size_bytes INTEGER NOT NULL,
            checksum TEXT NOT NULL,
            encryption_key_id TEXT NOT NULL,
            storage_location TEXT NOT NULL, -- Stored as JSON string
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            is_immutable INTEGER DEFAULT 0,
            version INTEGER DEFAULT 1,
            metadata TEXT DEFAULT "{}", -- Stored as JSON string
            FOREIGN KEY (owner_id) REFERENCES omega_accounts(account_id)
        );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_storage_owner_id ON omega_storage_metadata(owner_id);")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_storage_owner_object_name ON omega_storage_metadata(owner_id, object_name);")

    # Table: omega_api_keys
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS omega_api_keys (
            key_id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL,
            key_alias TEXT NOT NULL,
            api_key_hash TEXT NOT NULL,
            api_secret_hash TEXT,
            key_type TEXT NOT NULL,
            permissions TEXT DEFAULT "[]", -- Stored as JSON string
            status TEXT DEFAULT "ACTIVE",
            created_at TEXT NOT NULL,
            expires_at TEXT,
            last_used_at TEXT,
            FOREIGN KEY (owner_id) REFERENCES omega_accounts(account_id)
        );
    """)
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_api_key_owner_alias ON omega_api_keys(owner_id, key_alias);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_key_status ON omega_api_keys(status);")

    # Table: omega_encryption_keys
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS omega_encryption_keys (
            key_id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL,
            key_material_encrypted TEXT NOT NULL,
            key_type TEXT NOT NULL,
            status TEXT DEFAULT "ACTIVE",
            created_at TEXT NOT NULL,
            revoked_at TEXT,
            FOREIGN KEY (owner_id) REFERENCES omega_accounts(account_id)
        );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_encryption_key_owner_id ON omega_encryption_keys(owner_id);")

    # Table: omega_ledger_events (NEW - for event sourcing)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS omega_ledger_events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL, -- e.g., 'TransactionInitiated', 'WalletCredited'
            aggregate_id TEXT NOT NULL, -- ID of the entity the event applies to (e.g., wallet_id, transaction_id)
            aggregate_type TEXT NOT NULL, -- Type of the entity (e.g., 'wallet', 'transaction')
            owner_id TEXT NOT NULL,
            event_data TEXT NOT NULL, -- JSON string of event details
            timestamp TEXT NOT NULL,
            previous_event_hash TEXT, -- For chaining events (blockchain-like)
            event_hash TEXT NOT NULL UNIQUE,
            FOREIGN KEY (owner_id) REFERENCES omega_accounts(account_id)
        );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_aggregate_id ON omega_ledger_events(aggregate_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_owner_id ON omega_ledger_events(owner_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON omega_ledger_events(timestamp);")

    # Table: omega_consensus_votes (NEW - for transaction finality)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS omega_consensus_votes (
            vote_id TEXT PRIMARY KEY,
            transaction_id TEXT NOT NULL,
            node_id TEXT NOT NULL,
            vote_status TEXT NOT NULL, -- 'APPROVED', 'REJECTED'
            timestamp TEXT NOT NULL,
            FOREIGN KEY (transaction_id) REFERENCES omega_ledger_events(aggregate_id) ON DELETE CASCADE,
            FOREIGN KEY (node_id) REFERENCES omega_nodes(node_id)
        );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_consensus_transaction_id ON omega_consensus_votes(transaction_id);")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_consensus_transaction_node ON omega_consensus_votes(transaction_id, node_id);")

    # Table: omega_wallets
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS omega_wallets (
            wallet_id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL,
            balance REAL DEFAULT 0.0,
            currency TEXT DEFAULT "USD",
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (owner_id) REFERENCES omega_accounts(account_id)
        );
    """)
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_wallet_owner_id ON omega_wallets(owner_id, wallet_id);")

    # Table: omega_nodes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS omega_nodes (
            node_id TEXT PRIMARY KEY,
            node_type TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            owner_id TEXT NOT NULL,
            status TEXT DEFAULT "ACTIVE",
            last_heartbeat TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (owner_id) REFERENCES omega_accounts(account_id)
        );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_node_owner_id ON omega_nodes(owner_id);")

    conn.commit()
    conn.close()


# Example usage (for testing migration)
if __name__ == "__main__":
    print(f"Ensuring database {DATABASE_FILE} and tables exist...")
    migrate_db()
    print("Database migration complete.")

    # Test inserting a dummy account and wallet
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        owner_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("INSERT INTO omega_accounts (account_id, account_name, created_at, updated_at) VALUES (?, ?, ?, ?)",
                       (owner_id, "TestOwner", now, now))
        conn.commit()
        print(f"Inserted dummy account: {owner_id}")

        wallet_id = f"wallet_{owner_id}"
        cursor.execute("INSERT INTO omega_wallets (wallet_id, owner_id, balance, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                       (wallet_id, owner_id, 100.0, now, now))
        conn.commit()
        print(f"Inserted dummy wallet: {wallet_id} for owner {owner_id}")

        cursor.execute("SELECT * FROM omega_wallets WHERE wallet_id = ?", (wallet_id,))
        row = cursor.fetchone()
        if row:
            print(f"Retrieved wallet: {dict(row)}")

    except sqlite3.IntegrityError as e:
        print(f"Error inserting account/wallet (might already exist): {e}")
    finally:
        conn.close()
