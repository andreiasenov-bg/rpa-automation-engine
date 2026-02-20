#!/bin/bash
LOG=/tmp/auto_deploy.log
echo "[$(date)] Auto-deploy watcher started" >> $LOG
while true; do
  cd /repo
  LOCAL=$(git rev-parse HEAD 2>/dev/null)
  git fetch origin main -q 2>/dev/null
  REMOTE=$(git rev-parse origin/main 2>/dev/null)
  if [ -n "$LOCAL" ] && [ -n "$REMOTE" ] && [ "$LOCAL" != "$REMOTE" ]; then
    echo "[$(date)] New commits detected, deploying..." >> $LOG
    git pull origin main -q 2>>$LOG
    CHANGED=$(git diff --name-only $LOCAL $REMOTE 2>/dev/null)
    if echo "$CHANGED" | grep -q "^frontend/"; then
      echo "[$(date)] Frontend changes, rebuilding..." >> $LOG
      cd /repo/frontend && npm run build >>$LOG 2>&1
    fi
    echo "[$(date)] Deploy complete." >> $LOG
  fi
  sleep 60
done
