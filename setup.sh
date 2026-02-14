#!/usr/bin/env bash
# ── RPA Automation Engine — One-Click Setup ──
# Usage: chmod +x setup.sh && ./setup.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

echo -e "${CYAN}${BOLD}"
echo "╔═══════════════════════════════════════════════╗"
echo "║     RPA Automation Engine — Setup             ║"
echo "╚═══════════════════════════════════════════════╝"
echo -e "${NC}"

# ── 1. Check prerequisites ──
echo -e "${BLUE}[1/5]${NC} Checking prerequisites..."

# Check Docker
if ! command -v docker &>/dev/null; then
    echo -e "${RED}✗ Docker is not installed.${NC}"
    echo ""
    echo "  Install Docker Desktop from: https://www.docker.com/products/docker-desktop/"
    echo "  After installing, restart your terminal and run this script again."
    exit 1
fi
echo -e "  ${GREEN}✓${NC} Docker found: $(docker --version | head -1)"

# Check Docker Compose (v2)
if docker compose version &>/dev/null; then
    COMPOSE_CMD="docker compose"
    echo -e "  ${GREEN}✓${NC} Docker Compose found: $(docker compose version | head -1)"
elif command -v docker-compose &>/dev/null; then
    COMPOSE_CMD="docker-compose"
    echo -e "  ${GREEN}✓${NC} docker-compose found: $(docker-compose --version | head -1)"
else
    echo -e "${RED}✗ Docker Compose is not installed.${NC}"
    echo "  Docker Desktop includes Compose. Make sure Docker Desktop is running."
    exit 1
fi

# Check Docker daemon
if ! docker info &>/dev/null 2>&1; then
    echo -e "${RED}✗ Docker daemon is not running.${NC}"
    echo "  Start Docker Desktop and try again."
    exit 1
fi
echo -e "  ${GREEN}✓${NC} Docker daemon is running"

# ── 2. Create .env if it doesn't exist ──
echo ""
echo -e "${BLUE}[2/5]${NC} Setting up environment..."

if [ ! -f .env ]; then
    cp .env.example .env

    # Generate unique Fernet encryption key
    if command -v python3 &>/dev/null; then
        NEW_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || echo "")
        if [ -n "$NEW_KEY" ]; then
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s|ENCRYPTION_KEY=.*|ENCRYPTION_KEY=${NEW_KEY}|" .env
            else
                sed -i "s|ENCRYPTION_KEY=.*|ENCRYPTION_KEY=${NEW_KEY}|" .env
            fi
            echo -e "  ${GREEN}✓${NC} Generated unique encryption key"
        fi
    fi

    echo -e "  ${GREEN}✓${NC} Created .env from .env.example"
    echo -e "  ${YELLOW}ℹ${NC} Default admin credentials:"
    echo -e "    Email:    ${BOLD}admin@rpa-engine.local${NC}"
    echo -e "    Password: ${BOLD}admin123!${NC}"
else
    echo -e "  ${GREEN}✓${NC} .env already exists (keeping current values)"
fi

# ── 3. Build images ──
echo ""
echo -e "${BLUE}[3/5]${NC} Building Docker images (this may take 2-5 minutes on first run)..."
$COMPOSE_CMD build --quiet 2>&1 | while IFS= read -r line; do
    echo -e "  ${line}"
done
echo -e "  ${GREEN}✓${NC} Images built successfully"

# ── 4. Start services ──
echo ""
echo -e "${BLUE}[4/5]${NC} Starting services..."
$COMPOSE_CMD up -d

echo ""
echo -e "${BLUE}[5/5]${NC} Waiting for services to be healthy..."

# Wait for PostgreSQL
echo -n "  PostgreSQL: "
for i in $(seq 1 30); do
    if $COMPOSE_CMD exec -T postgres pg_isready -U rpa_user -d rpa_engine &>/dev/null; then
        echo -e "${GREEN}✓ Ready${NC}"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo -e "${RED}✗ Timed out${NC}"
        echo "  Check logs: $COMPOSE_CMD logs postgres"
        exit 1
    fi
    echo -n "."
    sleep 2
done

# Wait for Redis
echo -n "  Redis:      "
for i in $(seq 1 15); do
    if $COMPOSE_CMD exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; then
        echo -e "${GREEN}✓ Ready${NC}"
        break
    fi
    if [ "$i" -eq 15 ]; then
        echo -e "${RED}✗ Timed out${NC}"
        exit 1
    fi
    echo -n "."
    sleep 2
done

# Wait for Backend
echo -n "  Backend:    "
for i in $(seq 1 45); do
    if curl -sf http://localhost:8000/api/v1/health &>/dev/null; then
        echo -e "${GREEN}✓ Ready${NC}"
        break
    fi
    if [ "$i" -eq 45 ]; then
        echo -e "${YELLOW}⚠ Still starting (migrations may be running)${NC}"
        echo "  Check progress: $COMPOSE_CMD logs -f backend"
    fi
    echo -n "."
    sleep 3
done

# Wait for Frontend
echo -n "  Frontend:   "
for i in $(seq 1 20); do
    if curl -sf http://localhost:3000/health &>/dev/null; then
        echo -e "${GREEN}✓ Ready${NC}"
        break
    fi
    if [ "$i" -eq 20 ]; then
        echo -e "${YELLOW}⚠ Still starting${NC}"
    fi
    echo -n "."
    sleep 2
done

# ── Done! ──
echo ""
echo -e "${GREEN}${BOLD}╔═══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║          ✅  Setup Complete!                   ║${NC}"
echo -e "${GREEN}${BOLD}╚═══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}🌐 Open in browser:${NC}  ${CYAN}http://localhost:3000${NC}"
echo ""
echo -e "  ${BOLD}Login:${NC}"
echo -e "    Email:    ${CYAN}admin@rpa-engine.local${NC}"
echo -e "    Password: ${CYAN}admin123!${NC}"
echo ""
echo -e "  ${BOLD}Useful URLs:${NC}"
echo -e "    Frontend:   http://localhost:3000"
echo -e "    Backend:    http://localhost:8000"
echo -e "    API Docs:   http://localhost:8000/docs"
echo ""
echo -e "  ${BOLD}Commands:${NC}"
echo -e "    make dev-logs     — View logs"
echo -e "    make down         — Stop services"
echo -e "    make dev          — Start again"
echo -e "    make clean        — Reset everything"
echo ""
