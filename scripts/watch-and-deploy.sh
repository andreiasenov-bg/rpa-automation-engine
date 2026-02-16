#!/bin/bash
# Watch for new commits on main and auto-deploy
# Usage: nohup ~/rpa-automation-engine/scripts/watch-and-deploy.sh &
# Works from ANY directory. Checks every 30 seconds.

# Find repo dir — works even if invoked from outside the repo
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
if [ -d "$SCRIPT_DIR/../.git" ]; then
    REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
elif [ -d "$HOME/rpa-automation-engine/.git" ]; then
    REPO_DIR="$HOME/rpa-automation-engine"
else
    echo "[AUTO-DEPLOY] ERROR: Cannot find repo. Clone it to ~/rpa-automation-engine"
    exit 1
fi
cd "$REPO_DIR" || exit 1

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
        # Restart frontend to clear Vite cache (volume mounts don't trigger file watchers)
        docker compose restart frontend 2>/dev/null
        LAST_SHA="$REMOTE_SHA"
        echo "[AUTO-DEPLOY] $(date '+%H:%M:%S') Deploy complete!"
        echo ""
    fi

    sleep 30
done
