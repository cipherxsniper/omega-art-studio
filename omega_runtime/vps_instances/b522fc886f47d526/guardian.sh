#!/data/data/com.termux/files/usr/bin/bash
LOG="/data/data/com.termux/files/home/omega_runtime/vps_instances/b522fc886f47d526/logs/guardian.log"
if ! pgrep -f "server.py.*6002" > /dev/null 2>&1; then
    nohup python3 "/data/data/com.termux/files/home/omega_runtime/vps_instances/b522fc886f47d526/server.py" >> "$LOG" 2>&1 &
    echo "[$(date -u)] RESTARTED instance b522fc88" >> "$LOG"
fi
