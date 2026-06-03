FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# OS deps for asyncpg + lxml etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

COPY apps/curator/requirements.txt .
RUN pip install -r requirements.txt

COPY apps/curator/ ./

USER 10001:10001

HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
  CMD curl -fs http://127.0.0.1:8060/healthz || exit 1

EXPOSE 8060

CMD ["python", "main.py", "--config", "env.yaml", "--consume"]
