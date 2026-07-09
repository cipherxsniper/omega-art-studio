#!/data/data/com.termux/files/usr/bin/bash
LOG="/data/data/com.termux/files/home/omega_runtime/vps_instances/5a1c35f44d956d98/logs/guardian.log"
if ! pgrep -f "server.py.*6000" > /dev/null 2>&1; then
    nohup python3 "/data/data/com.termux/files/home/omega_runtime/vps_instances/5a1c35f44d956d98/server.py" >> "$LOG" 2>&1 &
    echo "[$(date -u)] RESTARTED instance 5a1c35f4" >> "$LOG"
fi
