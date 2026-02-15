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

# Install runtime system deps + Chromium browser dependencies for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    postgresql-client \
    redis-tools \
    tini \
    # Playwright Chromium system dependencies
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libxkbcommon0 \
    libatspi2.0-0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libpango-1.0-0 libcairo2 \
    libasound2 libxshmfence1 fonts-liberation fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-built Python packages from builder
COPY --from=builder /install /usr/local

# Create non-root user FIRST, then install Playwright as that user
RUN adduser --disabled-password --gecos '' appuser

# Install Playwright Chromium as appuser so binary lands in /home/appuser/.cache
ENV PLAYWRIGHT_BROWSERS_PATH=/home/appuser/.cache/ms-playwright
RUN mkdir -p /home/appuser/.cache && chown -R appuser:appuser /home/appuser
USER appuser
RUN python -m playwright install chromium
USER root

# Copy application code
COPY . .

# Make entrypoint executable and set ownership
RUN chmod +x scripts/entrypoint.sh \
    && chown -R appuser:appuser /app

# Also install pandas for script tasks
RUN pip install --no-cache-dir pandas

USER appuser
ENV PLAYWRIGHT_BROWSERS_PATH=/home/appuser/.cache/ms-playwright

EXPOSE 8000

# Use tini as init process for proper signal handling
ENTRYPOINT ["tini", "--", "scripts/entrypoint.sh"]
