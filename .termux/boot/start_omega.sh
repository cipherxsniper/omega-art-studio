#!/data/data/com.termux/files/usr/bin/bash
sleep 15
cd /data/data/com.termux/files/home
source ~/.env 2>/dev/null

# Start Tor
tor &
sleep 8

# Start SSH tunnel
nohup ssh -i ~/.ssh/omega_bridge \
  -o StrictHostKeyChecking=no \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=5 \
  -L 5432:127.0.0.1:5432 \
  u0_a253@192.168.11.163 -p 8022 -N \
  >> ~/omega_runtime/logs/ssh_tunnel.log 2>&1 &
sleep 10

# Start tunnel watchdog
nohup python3 ~/omega_tunnel_watchdog.py \
  >> ~/omega_runtime/logs/watchdog.log 2>&1 &

# Start main system
nohup python3 ~/omega_v10.py \
  >> ~/omega_runtime/logs/omega_v10.log 2>&1 &
sleep 15

# Auto score after boot
export PGPASSWORD='omega'
python3 ~/omega_oracle_v2.py >> ~/omega_runtime/logs/boot.log 2>&1

echo "[$(date)] Boot complete" >> ~/omega_runtime/logs/boot.log
nohup python3 ~/omega_master_guardian.py >> ~/omega_runtime/logs/guardian.log 2>&1 &
