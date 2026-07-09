#!/bin/bash
# OMEGA TUNNEL DAEMON
# Keeps SSH tunnel to Phone 2 alive FOREVER
# Auto-reconnects on drop, verifies PostgreSQL, never gives up

SSH_KEY="/data/data/com.termux/files/home/.ssh/omega_bridge"
PHONE2="192.168.11.163"
LOGS="/data/data/com.termux/files/home/omega_runtime/logs"
RETRY=0

mkdir -p "$LOGS"
echo "[$(date)] Tunnel daemon started" >> "$LOGS/tunnel_daemon.log"

while true; do
    # Check if tunnel is alive AND PostgreSQL is reachable
    if pgrep -f "ssh.*omega_bridge" > /dev/null 2>&1; then
        # Tunnel process exists — verify it actually works
        psql -h 127.0.0.1 -p 5432 -U postgres \
          -c "SELECT 1" > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            RETRY=0
            sleep 15
            continue
        fi
    fi

    # Tunnel dead or broken — restart it
    RETRY=$((RETRY + 1))
    echo "[$(date)] Tunnel down (attempt $RETRY) — reconnecting..." \
      >> "$LOGS/tunnel_daemon.log"

    # Kill any zombie tunnel processes
    pkill -f "ssh.*omega_bridge" 2>/dev/null
    sleep 2

    # Reconnect
    ssh -i "$SSH_KEY" \
      -o StrictHostKeyChecking=no \
      -o ServerAliveInterval=10 \
      -o ServerAliveCountMax=3 \
      -o ConnectTimeout=10 \
      -o ExitOnForwardFailure=yes \
      -o TCPKeepAlive=yes \
      -L 5432:127.0.0.1:5432 \
      u0_a253@$PHONE2 -p 8022 -N \
      >> "$LOGS/tunnel_daemon.log" 2>&1 &

    sleep 8

    # Verify
    psql -h 127.0.0.1 -p 5432 -U postgres \
      -c "SELECT 1" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "[$(date)] Tunnel RESTORED after $RETRY attempts" \
          >> "$LOGS/tunnel_daemon.log"
        RETRY=0

        # Also restart Phone 2 services if they died
        ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no \
          -o ConnectTimeout=5 \
          u0_a253@$PHONE2 -p 8022 \
          "pgrep sshd > /dev/null || sshd; \
           pg_ctl status -D \$PREFIX/var/lib/postgresql > /dev/null 2>&1 \
           || pg_ctl start -D \$PREFIX/var/lib/postgresql; \
           pgrep -f omega_consensus > /dev/null || \
           (cd ~/Omega-Production/omega_bank && \
            OMEGA_NODE_ID=omega-node-002 OMEGA_NODE_HOST=192.168.11.163 \
            setsid python3 omega_consensus.py \
            >> ~/omega_runtime/logs/consensus.log 2>&1 </dev/null &); \
           pgrep -f omega_node_manager > /dev/null || \
           (cd ~/Omega-Production/omega_bank && \
            OMEGA_NODE_ID=omega-node-002 OMEGA_NODE_HOST=192.168.11.163 \
            setsid python3 omega_node_manager.py \
            >> ~/omega_runtime/logs/node_manager.log 2>&1 </dev/null &)" \
          >> "$LOGS/tunnel_daemon.log" 2>&1 &
    else
        echo "[$(date)] Tunnel FAILED after attempt $RETRY" \
          >> "$LOGS/tunnel_daemon.log"
        sleep $((RETRY * 5 > 60 ? 60 : RETRY * 5))
    fi
done
