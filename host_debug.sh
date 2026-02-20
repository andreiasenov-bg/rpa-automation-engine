#!/bin/bash
cd /opt/rpa-engine
docker logs rpa-backend --tail 100 > /opt/rpa-engine/backend_logs.txt 2>&1
docker ps -a > /opt/rpa-engine/docker_status.txt 2>&1
docker compose -f docker-compose.yml -f docker-compose.hetzner.yml up -d deployer >> /opt/rpa-engine/recreate_log.txt 2>&1
echo DONE >> /opt/rpa-engine/backend_logs.txt
