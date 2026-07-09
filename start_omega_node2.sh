#!/data/data/com.termux/files/usr/bin/bash
# ─────────────────────────────────────────────
# Omega Node 2 — Termux Boot Script
# Place at: ~/.termux/boot/start_omega_node2.sh
# chmod +x ~/.termux/boot/start_omega_node2.sh
# Requires: Termux:Boot app installed
# ─────────────────────────────────────────────

LOG="$HOME/omega_runtime/logs/boot.log"
mkdir -p "$HOME/omega_runtime/logs"

echo "[$(date)] Boot script started" >> "$LOG"

# 1. Start sshd
pkill -f sshd 2>/dev/null
sleep 1
sshd
echo "[$(date)] sshd started" >> "$LOG"

# 2. Start PostgreSQL
pg_ctl status -D "$PREFIX/var/lib/postgresql" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    pg_ctl start -D "$PREFIX/var/lib/postgresql" \
        -l "$HOME/omega_runtime/logs/postgres.log"
    sleep 5
    echo "[$(date)] PostgreSQL started" >> "$LOG"
else
    echo "[$(date)] PostgreSQL already running" >> "$LOG"
fi

# 3. Wait for PostgreSQL to be ready
for i in $(seq 1 10); do
    psql -U postgres -d omega_bank -c "SELECT 1;" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "[$(date)] PostgreSQL ready" >> "$LOG"
        break
    fi
    sleep 2
done

# 4. Start consensus node
pkill -f omega_consensus 2>/dev/null
sleep 1

cd "$HOME/Omega-Production/omega_bank"
OMEGA_NODE_ID=omega-node-002 \
OMEGA_NODE_HOST=192.168.11.163 \
nohup python3 omega_consensus.py \
    >> "$HOME/omega_runtime/logs/consensus.log" 2>&1 &

echo "[$(date)] omega-node-002 started PID: $!" >> "$LOG"

# 5. Watchdog loop — restart anything that dies
while true; do
    # Check sshd
    if ! pgrep -f sshd > /dev/null; then
        echo "[$(date)] sshd died — restarting" >> "$LOG"
        sshd
    fi

    # Check PostgreSQL
    psql -U postgres -d omega_bank -c "SELECT 1;" > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "[$(date)] PostgreSQL died — restarting" >> "$LOG"
        pg_ctl start -D "$PREFIX/var/lib/postgresql" \
            -l "$HOME/omega_runtime/logs/postgres.log"
        sleep 5
    fi

    # Check consensus node
    if ! pgrep -f omega_consensus > /dev/null; then
        echo "[$(date)] omega_consensus died — restarting" >> "$LOG"
        cd "$HOME/Omega-Production/omega_bank"
        OMEGA_NODE_ID=omega-node-002 \
        OMEGA_NODE_HOST=192.168.11.163 \
        nohup python3 omega_consensus.py \
            >> "$HOME/omega_runtime/logs/consensus.log" 2>&1 &
        echo "[$(date)] omega-node-002 restarted PID: $!" >> "$LOG"
    fi

    sleep 30
done
