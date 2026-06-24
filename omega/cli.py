
import argparse
import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any

# Import necessary components from the API server script
# In a real setup, these would be in separate modules and imported directly.
from omega_cloud_node3_api_server import OmegaAuthSystem, OmegaCloudDB, migrate_db

def create_owner(owner_name: str) -> Dict[str, Any]:
    owner_id = str(uuid.uuid4())
    # In a real system, you'd have an 'owners' table.
    # For now, we'll just return the ID and assume it's valid for key generation.
    print(f"Successfully created new owner: {owner_name} with ID: {owner_id}")
    return {"owner_id": owner_id, "owner_name": owner_name}

def generate_api_key_cli(owner_id: str, key_alias: str, key_type: str, permissions: List[str], expires_in_days: int = 365):
    if not permissions:
        print("Warning: No permissions specified. The key might be severely limited.")

    key_info = OmegaAuthSystem.generate_api_key(
        owner_id=owner_id,
        key_alias=key_alias,
        key_type=key_type,
        permissions=permissions,
        expires_in_days=expires_in_days
    )
    print("\n--- API Key Generated Successfully ---")
    print(f"Key ID: {key_info['key_id']}")
    print(f"Key Type: {key_info['key_type']}")
    print(f"Key Alias: {key_alias}")
    print(f"Expires At: {key_info['expires_at'] or 'Never'}")
    print(f"Permissions: {permissions}")
    print("\n--- IMPORTANT: Store these credentials securely! ---")
    print(f"API Key: {key_info['api_key']}")
    if key_type == "HMAC":
        print(f"API Secret: {key_info['api_secret']}")
    print("----------------------------------------")

def list_api_keys_cli(owner_id: str = None):
    conn = OmegaCloudDB.get_db_connection()
    cursor = conn.cursor()
    query = "SELECT key_id, owner_id, key_alias, key_type, status, created_at, expires_at, last_used_at, permissions FROM omega_api_keys"
    params = []
    if owner_id:
        query += " WHERE owner_id = ?"
        params.append(owner_id)
    
    cursor.execute(query, tuple(params))
    keys = cursor.fetchall()
    conn.close()

    if not keys:
        print("No API keys found.")
        return

    print("\n--- Omega Cloud API Keys ---")
    for key in keys:
        key_dict = dict(key)
        key_dict['permissions'] = json.loads(key_dict['permissions']) # Deserialize permissions
        print(f"Key ID: {key_dict['key_id']}")
        print(f"  Owner ID: {key_dict['owner_id']}")
        print(f"  Alias: {key_dict['key_alias']}")
        print(f"  Type: {key_dict['key_type']}")
        print(f"  Status: {key_dict['status']}")
        print(f"  Created: {key_dict['created_at']}")
        print(f"  Expires: {key_dict['expires_at'] or 'Never'}")
        print(f"  Last Used: {key_dict['last_used_at'] or 'Never'}")
        print(f"  Permissions: {key_dict['permissions']}")
        print("----------------------------")

def main():
    parser = argparse.ArgumentParser(description="Omega Cloud Service CLI for management.")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: init-db
    init_db_parser = subparsers.add_parser("init-db", help="Initialize or migrate the database schema.")

    # Command: create-owner
    create_owner_parser = subparsers.add_parser("create-owner", help="Create a new owner for the Omega Cloud Service.")
    create_owner_parser.add_argument("owner_name", type=str, help="Name of the new owner.")

    # Command: generate-key
    generate_key_parser = subparsers.add_parser("generate-key", help="Generate a new API key for an owner.")
    generate_key_parser.add_argument("owner_id", type=str, help="ID of the owner for whom to generate the key.")
    generate_key_parser.add_argument("key_alias", type=str, help="A memorable alias for the API key.")
    generate_key_parser.add_argument("--type", choices=["BEARER", "HMAC"], default="BEARER", help="Type of API key to generate (BEARER or HMAC).")
    generate_key_parser.add_argument("--permissions", nargs="*", default=[], help="Space-separated list of permissions (e.g., storage:read ledger:post_transaction).")
    generate_key_parser.add_argument("--expires-in-days", type=int, default=365, help="Number of days until the key expires (default: 365).")

    # Command: list-keys
    list_keys_parser = subparsers.add_parser("list-keys", help="List existing API keys.")
    list_keys_parser.add_argument("--owner-id", type=str, help="Filter keys by owner ID.")

    args = parser.parse_args()

    if args.command == "init-db":
        print("Initializing/Migrating Omega Cloud database...")
        migrate_db()
        print("Database initialization/migration complete.")
    elif args.command == "create-owner":
        create_owner(args.owner_name)
    elif args.command == "generate-key":
        generate_api_key_cli(args.owner_id, args.key_alias, args.type, args.permissions, args.expires_in_days)
    elif args.command == "list-keys":
        list_api_keys_cli(args.owner_id)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
