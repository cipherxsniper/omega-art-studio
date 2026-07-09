#!/usr/bin/env python3
"""
OMEGA NAT PUNCH-THROUGH ENGINE v1.0
Pure Python. Zero dependencies. Zero third parties.

How it works:
- Both phones send UDP packets to each other's public IP
- This opens a hole in each router's NAT table
- Once both holes are open, direct P2P connection established
- No relay. No server. No signup. Just physics.

This is how BitTorrent works. How WebRTC works.
We're building it from scratch in 100 lines.
"""
import socket, threading, time, json, sys, os
from datetime import datetime

class OmegaNATPunch:
    def __init__(self, local_port=7460):
        self.local_port = local_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("0.0.0.0", local_port))
        self.sock.settimeout(2)
        self.peers = {}
        self.running = False
        self.node_id = os.getenv("OMEGA_NODE_ID", f"omega-punch-{local_port}")

    def get_public_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "unknown"

    def punch(self, target_ip, target_port, attempts=10):
        """Send UDP packets to punch hole in NAT."""
        print(f"Punching hole to {target_ip}:{target_port}...")
        msg = json.dumps({
            "type": "punch",
            "node_id": self.node_id,
            "ts": datetime.now().isoformat()
        }).encode()
        for i in range(attempts):
            try:
                self.sock.sendto(msg, (target_ip, target_port))
                print(f"  Punch {i+1}/{attempts} sent")
                time.sleep(0.5)
            except Exception as e:
                print(f"  Punch failed: {e}")
        print(f"Hole punch complete. Waiting for response...")

    def listen(self, callback=None):
        """Listen for incoming punched connections."""
        self.running = True
        print(f"Listening on port {self.local_port}...")
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                msg = json.loads(data.decode())
                peer_id = msg.get("node_id", str(addr))
                self.peers[peer_id] = {
                    "addr": addr,
                    "last_seen": datetime.now().isoformat(),
                    "type": msg.get("type")
                }
                print(f"  Peer connected: {peer_id} @ {addr[0]}:{addr[1]}")
                # Send back acknowledgment
                ack = json.dumps({
                    "type": "ack",
                    "node_id": self.node_id,
                    "peer": peer_id,
                    "ts": datetime.now().isoformat()
                }).encode()
                self.sock.sendto(ack, addr)
                if callback:
                    callback(peer_id, addr, msg)
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Listen error: {e}")

    def send(self, peer_id, data):
        """Send data to a known peer."""
        if peer_id not in self.peers:
            print(f"Unknown peer: {peer_id}")
            return False
        addr = self.peers[peer_id]["addr"]
        try:
            msg = json.dumps({"type": "data", "node_id": self.node_id,
                            "payload": data}).encode()
            self.sock.sendto(msg, addr)
            return True
        except Exception as e:
            print(f"Send failed: {e}")
            return False

    def broadcast(self, data):
        """Broadcast to all known peers."""
        for peer_id in list(self.peers.keys()):
            self.send(peer_id, data)

    def status(self):
        print(f"\n{'='*50}")
        print(f"  OMEGA NAT PUNCH ENGINE")
        print(f"  Node:    {self.node_id}")
        print(f"  Local:   {self.get_public_ip()}:{self.local_port}")
        print(f"  Peers:   {len(self.peers)}")
        for pid, pdata in self.peers.items():
            addr = pdata["addr"]
            print(f"    {pid} @ {addr[0]}:{addr[1]}")
        print(f"{'='*50}")

def phone1_mode():
    """Run on Phone 1 — initiates punch to Phone 2."""
    phone2_public_ip = input("Enter Phone 2 public IP (run curl https://api.ipify.org on Phone 2): ").strip()
    punch = OmegaNATPunch(local_port=7460)
    punch.node_id = "omega-node-001"
    print(f"\nPhone 1 public IP: {punch.get_public_ip()}")
    print(f"Tell Phone 2 to punch back to: {punch.get_public_ip()}:7460\n")
    # Start listening in background
    t = threading.Thread(target=punch.listen, daemon=True)
    t.start()
    # Punch hole to Phone 2
    punch.punch(phone2_public_ip, 7461)
    # Keep running
    while True:
        time.sleep(5)
        punch.status()
        # Send chain heartbeat to all peers
        punch.broadcast({"type": "heartbeat", "entries": 2005913})

def phone2_mode():
    """Run on Phone 2 — punches back to Phone 1."""
    phone1_public_ip = input("Enter Phone 1 public IP (23.162.0.62): ").strip()
    punch = OmegaNATPunch(local_port=7461)
    punch.node_id = "omega-node-002"
    t = threading.Thread(target=punch.listen, daemon=True)
    t.start()
    punch.punch(phone1_public_ip, 7460)
    while True:
        time.sleep(5)
        punch.status()

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "status"
    if mode == "phone1":
        phone1_mode()
    elif mode == "phone2":
        phone2_mode()
    elif mode == "status":
        punch = OmegaNATPunch(local_port=7460)
        punch.status()
    else:
        print("Usage: python3 omega_nat_punch.py [phone1|phone2|status]")
