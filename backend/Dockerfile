# ── Stage 1: Build dependencies ──
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runtime ──
FROM python:3.11-slim

WORKDIR /app

# Install only runtime system deps (no build-essential)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    postgresql-client \
    redis-tools \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-built Python packages from builder
COPY --from=builder /install /usr/local

# Install Playwright browsers (chromium) + system deps for headless browser
RUN python -m playwright install --with-deps chromium

# Copy application code
COPY . .

# Make entrypoint executable
RUN chmod +x scripts/entrypoint.sh

# Create non-root user — also own playwright browser cache
RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /app \
    && chown -R appuser:appuser /root/.cache 2>/dev/null || true
USER appuser

EXPOSE 8000

# Use tini as init process for proper signal handling
ENTRYPOINT ["tini", "--", "scripts/entrypoint.sh"]
