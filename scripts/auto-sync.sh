#!/bin/bash
###############################################################################
# auto-sync.sh — Permanent auto-sync for RPA Engine
# Watches for local file changes → commit → push → redeploy containers
# Runs as systemd service: rpa-auto-sync.service
###############################################################################

set -euo pipefail

REPO_DIR="/opt/rpa-engine"
LOG_FILE="/var/log/rpa-auto-sync.log"
LOCKFILE="/tmp/rpa-auto-sync.lock"
DEBOUNCE_SECONDS=5
COMPOSE_CMD="docker compose -f ${REPO_DIR}/docker-compose.yml --project-directory ${REPO_DIR} --env-file ${REPO_DIR}/.env"

# Directories to watch (relative to REPO_DIR)
WATCH_DIRS="backend frontend .github"

# Files/dirs to IGNORE (git-ignored stuff, logs, __pycache__, etc.)
IGNORE_PATTERN="(__pycache__|.pyc|node_modules|.git/|storage/|alembic/versions|.env|.log|dist/)"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

cleanup() { rm -f "$LOCKFILE"; log "Auto-sync stopped."; exit 0; }
trap cleanup EXIT INT TERM

# Prevent duplicate instances
if [ -f "$LOCKFILE" ]; then
  OLD_PID=$(cat "$LOCKFILE" 2>/dev/null)
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Auto-sync already running (PID $OLD_PID). Exiting."
    exit 1
  fi
fi
echo $$ > "$LOCKFILE"

cd "$REPO_DIR"

log "========================================="
log "RPA Auto-Sync started (PID $$)"
log "Watching: $WATCH_DIRS"
log "========================================="

do_sync() {
  cd "$REPO_DIR"

  # Check for actual changes
  local changes=$(git status --porcelain 2>/dev/null | grep -vE "$IGNORE_PATTERN" || true)
  if [ -z "$changes" ]; then
    return 0
  fi

  log "Changes detected:"
  echo "$changes" | head -20 | tee -a "$LOG_FILE"

  # Determine what changed for commit message and selective restart
  local backend_changed=false
  local frontend_changed=false
  local other_changed=false

  if echo "$changes" | grep -q "backend/"; then backend_changed=true; fi
  if echo "$changes" | grep -q "frontend/"; then frontend_changed=true; fi
  if echo "$changes" | grep -vq -E "backend/|frontend/"; then other_changed=true; fi

  # Build commit message from changed files
  local changed_files=$(echo "$changes" | awk '{print $2}' | head -5 | tr '\n' ', ' | sed 's/,$//')
  local file_count=$(echo "$changes" | wc -l | tr -d ' ')
  local msg="auto-sync: update ${file_count} file(s) — ${changed_files}"

  # Stage all changes (except secrets)
  git add -A
  # Unstage any secrets that might have been added
  git reset HEAD -- .env .env.* *.pem *.key 2>/dev/null || true

  # Commit
  if ! git diff --cached --quiet 2>/dev/null; then
    git commit -m "$msg" 2>&1 | tee -a "$LOG_FILE"
    log "Committed: $msg"
  else
    log "Nothing staged after filtering. Skipping."
    return 0
  fi

  # Push to GitHub (CI/CD will also deploy, but we deploy locally first for speed)
  if git push origin main 2>&1 | tee -a "$LOG_FILE"; then
    log "Pushed to GitHub successfully."
  else
    log "WARNING: Push failed. Will retry next cycle."
    return 1
  fi

  # Immediate local container restart for affected services
  if [ "$backend_changed" = true ]; then
    log "Restarting backend services..."
    $COMPOSE_CMD up -d --force-recreate backend celery-worker celery-beat 2>&1 | tee -a "$LOG_FILE"
  fi

  if [ "$frontend_changed" = true ]; then
    log "Rebuilding frontend..."
    $COMPOSE_CMD up -d --build frontend 2>&1 | tee -a "$LOG_FILE"
  fi

  log "Sync complete!"
  return 0
}

# Main loop: watch for file changes using inotifywait
WATCH_PATHS=""
for dir in $WATCH_DIRS; do
  if [ -d "${REPO_DIR}/${dir}" ]; then
    WATCH_PATHS="$WATCH_PATHS ${REPO_DIR}/${dir}"
  fi
done

log "Watching paths: $WATCH_PATHS"

while true; do
  # Wait for file changes (modify, create, delete, move)
  inotifywait -r -q \
    --exclude "$IGNORE_PATTERN" \
    -e modify -e create -e delete -e move \
    $WATCH_PATHS 2>/dev/null || {
      log "inotifywait error, falling back to polling..."
      sleep 30
      do_sync || true
      continue
    }

  # Debounce: wait a few seconds for batch changes to settle
  log "Change detected, waiting ${DEBOUNCE_SECONDS}s for batch changes..."
  sleep $DEBOUNCE_SECONDS

  # Drain any queued inotify events
  timeout 2 inotifywait -r -q \
    --exclude "$IGNORE_PATTERN" \
    -e modify -e create -e delete -e move \
    $WATCH_PATHS 2>/dev/null || true

  # Do the sync
  do_sync || log "Sync failed, will retry on next change."
done

