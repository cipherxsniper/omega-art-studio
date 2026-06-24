#!/data/data/com.termux/files/usr/bin/bash
# omega_bridge.sh — Full CD bridge Phone 1 + Phone 2 → GitHub
# I can read everything via raw.githubusercontent.com

OMEGA_HOME="/data/data/com.termux/files/home"
SSH_KEY="$OMEGA_HOME/.ssh/omega_bridge"
PHONE2="192.168.11.2"
cd "$OMEGA_HOME" || exit 1

echo "[$(date)] Bridge sync starting..." >> "$OMEGA_HOME/omega_runtime/logs/bridge.log"

# ── PHONE 1 FILE SNAPSHOT ──────────────────────────────────────
mkdir -p bridge/phone1 bridge/phone2

# Key Python files
for f in omega_v10.py omega_guardian.sh omega_provenance_api.py           omega_nft_webhook.py omega_collection_pipeline.py           omega_oracle_v2.py omega_sentinel.py omega_spawn_engine.py           omega_url_broker.py omega_gallery.html find2.sh; do
    [ -f "$OMEGA_HOME/$f" ] && cp "$OMEGA_HOME/$f" "bridge/phone1/$f"
done

# ── PHONE 1 LIVE STATUS ────────────────────────────────────────
cat > bridge/phone1/STATUS.md << STATUS
# OMEGA PHONE 1 — LIVE STATUS
**Generated:** $(date -u)

## Oracle Score
$(python3 "$OMEGA_HOME/omega_oracle_v2.py" 2>/dev/null | grep -A2 "ORACLE\|passing\|delta" | head -10)

## Running Processes
$(pgrep -af "omega|cloudflared|autossh" | grep -v grep | grep -v pgrep)

## Tunnel URLs
$(curl -s http://127.0.0.1:8085/current-all 2>/dev/null)

## Disk Usage Phone 1
$(du -sh "$OMEGA_HOME"/* 2>/dev/null | sort -rh | head -15)

## Guardian Log (last 20)
$(tail -20 "$OMEGA_HOME/omega_runtime/logs/guardian.log" 2>/dev/null)

## Spawn Log (last 10)
$(tail -10 "$OMEGA_HOME/omega_runtime/logs/spawn_engine.log" 2>/dev/null)

## NFT Registry Summary
$(psql -h 127.0.0.1 -p 5432 -U postgres -d omega_ledger -c "SELECT collection, COUNT(*) total, COUNT(CASE WHEN sale_status='sold' THEN 1 END) sold, COUNT(CASE WHEN sale_status='for_sale' THEN 1 END) for_sale FROM nft_registry GROUP BY collection ORDER BY collection;" 2>/dev/null)

## Recent Sales
$(psql -h 127.0.0.1 -p 5432 -U postgres -d omega_ledger -c "SELECT token_id, title, collection, rarity, sold_at FROM nft_registry WHERE sale_status='sold' ORDER BY sold_at DESC LIMIT 5;" 2>/dev/null)

## Wallet Balances
$(psql -h 127.0.0.1 -p 5432 -U postgres -d omega_bank -c "SELECT a.owner_name, w.settled_balance FROM wallets w JOIN accounts a ON w.account_id=a.account_id ORDER BY w.settled_balance DESC LIMIT 5;" 2>/dev/null)
STATUS

# ── PHONE 2 STATUS ─────────────────────────────────────────────
P2_STATUS=$(ssh -i "$SSH_KEY" -p 8022     -o ConnectTimeout=5     -o StrictHostKeyChecking=no     u0_a253@$PHONE2     "echo ONLINE &&      df -h /data | tail -1 &&      ps aux | grep postgres | grep -v grep | head -3 &&      psql -U postgres -d omega_bank -c 'SELECT COUNT(*) FROM wallets;' 2>/dev/null &&      psql -U postgres -d omega_ledger -c 'SELECT COUNT(*) FROM nft_registry;' 2>/dev/null &&      ls -la ~/omega_consensus.py 2>/dev/null" 2>/dev/null || echo "UNREACHABLE — run find2")

cat > bridge/phone2/STATUS.md << STATUS2
# OMEGA PHONE 2 — LIVE STATUS
**Generated:** $(date -u)

## Connection
$P2_STATUS

## Phone 2 Files (via SSH)
$(ssh -i "$SSH_KEY" -p 8022 -o ConnectTimeout=5 -o StrictHostKeyChecking=no     u0_a253@$PHONE2 "ls -la ~/*.py 2>/dev/null | head -20" 2>/dev/null || echo "Cannot list — SSH down")
STATUS2

# ── COMBINED INDEX ─────────────────────────────────────────────
cat > bridge/INDEX.md << INDEX
# OMEGA SYSTEM BRIDGE
**Last Sync:** $(date -u)
**Phone 1:** ONLINE
**Phone 2:** $(echo "$P2_STATUS" | grep -q "ONLINE" && echo "ONLINE" || echo "UNREACHABLE")

## Quick Links (raw GitHub)
- [Phone 1 Status](phone1/STATUS.md)
- [Phone 2 Status](phone2/STATUS.md)
- [Guardian](phone1/omega_guardian.sh)
- [Gallery](phone1/omega_gallery.html)
- [Provenance API](phone1/omega_provenance_api.py)
- [NFT Webhook](phone1/omega_nft_webhook.py)
- [Oracle](phone1/omega_oracle_v2.py)
INDEX

# ── PUSH TO GITHUB ─────────────────────────────────────────────
git add -A
git commit -m "bridge sync $(date -u '+%Y-%m-%d %H:%M UTC')" 2>/dev/null
git push origin master --force 2>/dev/null
echo "[$(date)] Bridge sync complete" >> "$OMEGA_HOME/omega_runtime/logs/bridge.log"
echo "BRIDGE SYNC COMPLETE"
