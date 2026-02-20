#!/bin/bash
# Fix script to run on host after rescue mode
cd /opt/rpa-engine
# Recreate all containers with updated compose config
docker compose -f docker-compose.yml -f docker-compose.hetzner.yml up -d --force-recreate
# Show status
docker ps
