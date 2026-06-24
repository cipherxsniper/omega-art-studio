#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP="omega_backup_$DATE.zip"
zip -r ~/storage/downloads/$BACKUP . --exclude "*.log" --exclude "*.db"
echo "Saved: ~/storage/downloads/$BACKUP"
