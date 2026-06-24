#!/data/data/com.termux/files/usr/bin/bash
sshd
sleep 5
OMEGA_NODE_ID=omega-node-002 OMEGA_NODE_HOST=192.168.11.163 nohup python3 ~/omega_consensus.py >> /data/data/com.termux/files/home/omega_runtime/logs/consensus_node2.log 2>&1 &
