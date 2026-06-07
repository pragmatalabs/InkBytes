FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    # Playwright stores browsers here; must be writable by non-root user.
    PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers \
    # Camoufox stores its binary alongside the package (default works fine).
    CAMOUFOX_EXECUTABLE_PATH=/opt/camoufox

WORKDIR /app

# OS deps for asyncpg + Playwright Chromium headless + Camoufox (Firefox-based)
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential libpq-dev curl \
      # Chromium / Playwright system deps
      libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
      libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
      libxrandr2 libgbm1 libasound2 libpango-1.0-0 libcairo2 \
      # Firefox / Camoufox system deps
      libdbus-glib-1-2 libgtk-3-0 libx11-xcb1 && \
    rm -rf /var/lib/apt/lists/*

COPY apps/curator/requirements.txt .
RUN pip install -r requirements.txt

# Install Playwright Chromium browser binary (used by DynamicFetcher).
# --with-deps skipped here — we installed OS deps explicitly above.
RUN mkdir -p /opt/playwright-browsers && \
    playwright install chromium

# Download Camoufox browser binary (used by StealthyFetcher).
RUN python -m camoufox fetch

COPY apps/curator/ ./

# Give non-root user read access to browser directories.
RUN chmod -R a+rX /opt/playwright-browsers /opt/camoufox 2>/dev/null || true

USER 10001:10001

HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
  CMD curl -fs http://127.0.0.1:8060/healthz || exit 1

EXPOSE 8060

CMD ["python", "main.py", "--config", "env.yaml", "--consume"]
