#!/data/data/com.termux/files/usr/bin/bash
# omega_autopush.sh — watches key files and auto-pushes to GitHub
# Runs every 60 seconds, only pushes if something changed

OMEGA_HOME="/data/data/com.termux/files/home"
GH_PAT=$(grep "GITHUB_PAT" "$OMEGA_HOME/.env" | tail -1 | cut -d'=' -f2 | tr -d ' ')
REPO="OMEGAOPS.AI"

cd "$OMEGA_HOME" || exit 1

# Generate STATUS.md with live system state
cat > STATUS.md << STATUS
# OMEGA LIVE STATUS
Generated: $(date -u)

## Oracle
$(python3 "$OMEGA_HOME/omega_oracle_v2.py" 2>/dev/null | tail -5)

## Cloudflared Tunnels
$(pgrep -af cloudflared | grep -v grep)

## PostgreSQL
$(psql -h 127.0.0.1 -p 5432 -U postgres -d omega_ledger -c "SELECT collection, COUNT(*), COUNT(CASE WHEN sale_status='sold' THEN 1 END) as sold FROM nft_registry GROUP BY collection;" 2>/dev/null)

## NFT Sales
$(psql -h 127.0.0.1 -p 5432 -U postgres -d omega_ledger -c "SELECT token_id, title, collection, rarity, owner_account_id, sold_at FROM nft_registry WHERE sale_status='sold' ORDER BY sold_at DESC LIMIT 10;" 2>/dev/null)

## Disk Usage
$(du -sh "$OMEGA_HOME"/* 2>/dev/null | sort -rh | head -10)

## Guardian Log (last 10)
$(tail -10 "$OMEGA_HOME/omega_runtime/logs/guardian.log" 2>/dev/null)

## Phone 2
$(ssh -i "$OMEGA_HOME/.ssh/omega_bridge" -p 8022 -o ConnectTimeout=3 -o StrictHostKeyChecking=no u0_a253@192.168.11.2 "echo ONLINE && df -h /data | tail -1" 2>/dev/null || echo "UNREACHABLE")
STATUS

# Check if anything changed
if git diff --quiet && git diff --cached --quiet; then
    # Only STATUS.md might have changed
    if git diff --quiet STATUS.md 2>/dev/null; then
        exit 0
    fi
fi

git add -A
git commit -m "auto-sync $(date -u '+%Y-%m-%d %H:%M UTC')"
git push origin master --force-with-lease 2>/dev/null || git push origin master --force
echo "[$(date)] Auto-pushed to GitHub" >> "$OMEGA_HOME/omega_runtime/logs/autopush.log"
