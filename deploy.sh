#!/bin/bash
set -euo pipefail
APP_DIR="/opt/rpa-engine"
COMPOSE_CMD="docker compose -f docker-compose.yml -f docker-compose.hetzner.yml"
cd "$APP_DIR"
echo "Pulling latest code..."
git pull origin main
echo "Building containers..."
$COMPOSE_CMD build --no-cache
echo "Starting services..."
$COMPOSE_CMD up -d
echo "Waiting for backend..."
for i in $(seq 1 60); do
    if curl -sf http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        echo "Backend is healthy!"
        break
    fi
    [ "$i" -eq 60 ] && echo "WARNING: Backend not responding after 60s"
    sleep 2
done
$COMPOSE_CMD ps
