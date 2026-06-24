#!/bin/bash
LOG="/data/data/com.termux/files/home/omega_runtime/logs/tunnel_daemon.log"
RECENT_COUNT=$(tail -100 "$LOG" 2>/dev/null | grep -c "killing and restarting" || echo 0)
test "$RECENT_COUNT" -le 25
