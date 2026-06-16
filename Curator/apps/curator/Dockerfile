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

# spaCy NER pre-pass models (ADR-0032 item 2). OFF by default to keep the image
# lean (~600MB of models) — build with `--build-arg INSTALL_NER_MODELS=true`
# AND set NER_ENABLED=1 at runtime to use the pass. es_core_news_lg is ~1GB
# resident; on the 1.5GB worker prefer es_core_news_md (NER_ES_MODEL) or wait
# for the 16GB droplet upgrade.
ARG INSTALL_NER_MODELS=false
RUN if [ "$INSTALL_NER_MODELS" = "true" ]; then \
      python -m spacy download en_core_web_md && \
      python -m spacy download es_core_news_lg ; \
    fi

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
