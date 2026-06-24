import sys
import os
sys.path.append(os.path.expanduser("~/omega_runtime"))
import omega_vps_engine

class OmegaStorageProvisioner:
    def __init__(self):
        self.storage_tier = "sovereign" # Verified valid tier
        self.email = "simpl3hoods@gmail.com"
        self.name = "Thomas Lee Harvey"

    def provision_storage_node(self, node_index):
        node_name = f"storage-node-{node_index:03d}"
        print(f"--- OMEGA HYPER-STORAGE PROVISIONING ---")
        print(f"Target: {node_name} | Tier: {self.storage_tier}")
        
        try:
            # Verified Signature Order: (email, name, tier, name)
            omega_vps_engine.provision(
                self.email,
                self.name,
                self.storage_tier,
                node_name
            )
            print(f"STATUS: {node_name} PROVISIONED")
            return True
        except Exception as e:
            print(f"PROVISIONING FAILED: {e}")
            return False

if __name__ == "__main__":
    provisioner = OmegaStorageProvisioner()
    provisioner.provision_storage_node(1)
