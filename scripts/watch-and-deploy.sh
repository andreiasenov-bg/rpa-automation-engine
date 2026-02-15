#!/bin/bash
# Watch for new commits on main and auto-deploy
# Run this once: nohup bash scripts/watch-and-deploy.sh &
# It checks every 30 seconds for new commits and rebuilds if needed.

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

LAST_SHA=""

echo "[AUTO-DEPLOY] Watching $REPO_DIR for changes..."
echo "[AUTO-DEPLOY] Press Ctrl+C to stop"

while true; do
    # Fetch latest from remote (silent)
    git fetch origin main --quiet 2>/dev/null

    # Get remote HEAD SHA
    REMOTE_SHA=$(git rev-parse origin/main 2>/dev/null)
    LOCAL_SHA=$(git rev-parse HEAD 2>/dev/null)

    if [ "$REMOTE_SHA" != "$LOCAL_SHA" ] && [ "$REMOTE_SHA" != "$LAST_SHA" ]; then
        echo ""
        echo "[AUTO-DEPLOY] $(date '+%H:%M:%S') New commits detected! Deploying..."
        git pull origin main
        docker compose up -d --build
        LAST_SHA="$REMOTE_SHA"
        echo "[AUTO-DEPLOY] $(date '+%H:%M:%S') Deploy complete!"
        echo ""
    fi

    sleep 30
done
