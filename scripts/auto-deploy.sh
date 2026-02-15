#!/bin/bash
# Auto-deploy script — triggered by GitHub webhook on push to main
# Pulls latest code and rebuilds Docker containers

set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_FILE="$REPO_DIR/deploy.log"

echo "$(date '+%Y-%m-%d %H:%M:%S') - Deploy triggered" >> "$LOG_FILE"

cd "$REPO_DIR"

# Pull latest
git pull origin main >> "$LOG_FILE" 2>&1

# Rebuild and restart
docker compose up -d --build >> "$LOG_FILE" 2>&1

echo "$(date '+%Y-%m-%d %H:%M:%S') - Deploy complete" >> "$LOG_FILE"
