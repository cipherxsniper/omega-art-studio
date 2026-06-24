import os
import json
import uuid
from datetime import datetime
from omega_node3 import OmegaCloudDB

class OmegaExpansionProtocol:
    def __init__(self):
        self.node_cost = 5000.00
        self.target_nodes = 10000

    def trigger_expansion(self):
        print("--- [REP] ANALYZING GROWTH CAPITAL ---")
        res = OmegaCloudDB._raw("SELECT SUM(balance) FROM omega_wallets", fetch="one")
        total_oc = res['SUM(balance)'] if res and res['SUM(balance)'] else 0
        
        res_count = OmegaCloudDB._raw("SELECT COUNT(*) FROM omega_nodes", fetch="one")
        current_nodes = res_count['COUNT(*)'] if res_count else 0
        
        # Keep 1M OC as operational reserve
        available = total_oc - 1000000.00
        to_spawn = int(available // self.node_cost)

        if to_spawn > 0 and current_nodes < self.target_nodes:
            print(f"ACTION: SPAWNING {to_spawn} NODES (COST: {to_spawn * self.node_cost:,.0f} OC).")
            for i in range(to_spawn):
                node_id = f"node-{current_nodes + i + 1:05d}"
                OmegaCloudDB.insert_node({"node_id": node_id, "node_type": "STORAGE_NODE", "endpoint": "http://mesh:5003", "owner_id": "omega-cloud-admin", "status": "ACTIVE", "last_heartbeat": datetime.now().isoformat(), "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()})
                OmegaCloudDB._raw("INSERT INTO omega_storage_metadata (object_id, owner_id, object_name, size_bytes, checksum, encryption_key_id, storage_location, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))", (str(uuid.uuid4()), "omega-cloud-admin", f"ALLOCATION_{node_id}", 100 * 1024 * 1024 * 1024, "OM856-RESERVED", "KEY_RESERVED", json.dumps({node_id: True})))
            OmegaCloudDB.upsert_wallet("wallet-node-0001", -(to_spawn * self.node_cost), "REP-EXPANSION")
            print(f"STATUS: {to_spawn} NODES PROVISIONED. TOTAL: {current_nodes + to_spawn}")
        else:
            print("STATUS: WAITING FOR CAPITAL ACCUMULATION.")

    def run(self):
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] OMEGA RECURSIVE EXPANSION ACTIVE")
        self.trigger_expansion()
        res = OmegaCloudDB._raw("SELECT COUNT(*) FROM omega_nodes", fetch="one")
        current = res['COUNT(*)']
        print(f"CAPACITY: {(current * 100) / 1024.0:.2f} TB / 1024.00 TB (1PB)")

if __name__ == "__main__":
    OmegaExpansionProtocol().run()
