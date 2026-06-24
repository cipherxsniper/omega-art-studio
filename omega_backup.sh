#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP="omega_backup_$DATE.zip"

zip -r ~/storage/downloads/$BACKUP \
    ~/omega_v10.py \
    ~/omega_start.sh \
    ~/omega_sentinel.py \
    ~/omega_oracle_v2.py \
    ~/omega_guardian.sh \
    ~/omega_node_manager.py \
    ~/omega_email_finder.py \
    ~/omega_card_engine.py \
    ~/.env \
    ~/omega_sentinel_snapshot.json \
    ~/omega_clean/

echo "Backup saved: ~/storage/downloads/$BACKUP"
