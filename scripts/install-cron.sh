#!/bin/bash
echo "0 3 * * * /opt/rpa-engine/scripts/backup-db.sh >> /var/log/rpa-backup.log 2>&1" | crontab -
crontab -l
