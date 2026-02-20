#!/bin/bash
# Host setup script for RPA Engine
# Run this ONCE on the host machine after deployment
set -e
echo "=== RPA Engine Host Setup ==="

# 1. Install Caddy config
echo "[1/4] Configuring Caddy..."
cp /root/rpa-automation-engine/Caddyfile /etc/caddy/Caddyfile
mkdir -p /var/log/caddy
systemctl restart caddy
echo "Caddy configured and restarted"

# 2. Recreate Docker containers with production config
echo "[2/4] Recreating Docker containers with production config..."
cd /root/rpa-automation-engine
docker compose -f docker-compose.yml -f docker-compose.hetzner.yml up -d --force-recreate
echo "Containers recreated"

# 3. Wait for services to come up
echo "[3/4] Waiting for services..."
sleep 15

# 4. Verify
echo "[4/4] Verifying..."
curl -sf http://localhost:8000/api/v1/health/ && echo "Backend: OK" || echo "Backend: FAILED"
curl -sf http://localhost:9000/status && echo "Deployer: OK" || echo "Deployer: FAILED"  
curl -sf http://localhost:80/ -o /dev/null && echo "Caddy: OK" || echo "Caddy: FAILED"

echo ""
echo "=== Setup Complete ==="
echo "Access your RPA Engine at: http://$(hostname -I | awk '{print $1}')"
