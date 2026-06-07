FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    # Playwright + Patchright share this browser dir; must be readable by non-root.
    PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers \
    PATCHRIGHT_BROWSERS_PATH=/opt/playwright-browsers

WORKDIR /app

# OS deps for asyncpg + Chromium headless (Playwright for DynamicFetcher,
# Patchright for StealthyFetcher — both use Chromium under the hood)
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential libpq-dev curl \
      libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
      libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
      libxrandr2 libgbm1 libasound2 libpango-1.0-0 libcairo2 && \
    rm -rf /var/lib/apt/lists/*

COPY apps/curator/requirements.txt .
RUN pip install -r requirements.txt

# Install Chromium binaries for both Playwright (DynamicFetcher) and
# Patchright (StealthyFetcher).  Both write to PLAYWRIGHT_BROWSERS_PATH.
RUN mkdir -p /opt/playwright-browsers && \
    playwright install chromium && \
    patchright install chromium

COPY apps/curator/ ./

# Give non-root user read access to browser directory.
RUN chmod -R a+rX /opt/playwright-browsers

USER 10001:10001

HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
  CMD curl -fs http://127.0.0.1:8060/healthz || exit 1

EXPOSE 8060

CMD ["python", "main.py", "--config", "env.yaml", "--consume"]
