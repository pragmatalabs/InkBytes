# syntax=docker/dockerfile:1
#
# Messor harvester image.
#
# Build context MUST be the Messor/ root — see docker/docker-compose.yaml:
#     build:
#       context: ..                 # -> Messor/
#       dockerfile: docker/Dockerfile
# so that both apps/scraper (the service) and packages/inkbytes (the
# self-contained shared kernel) are visible to the build.
#
# The shared kernel is installed from the build context via requirements.txt
# (`-e ../../packages/inkbytes`); it is NOT cloned from GitLab anymore.

# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.11 AS builder

WORKDIR /app

# Copy only the dependency manifests + the kernel first, so the (expensive) pip
# layer is cached and only re-runs when dependencies or the kernel change.
COPY apps/scraper/requirements.txt apps/scraper/pyproject.toml ./apps/scraper/
COPY packages/inkbytes ./packages/inkbytes

# Build the venv. requirements.txt declares the kernel as `-e ../../packages/inkbytes`,
# a path resolved relative to the current dir, so install from apps/scraper.
RUN python -m venv /app/venv && \
    /app/venv/bin/pip install --upgrade pip && \
    cd apps/scraper && \
    /app/venv/bin/pip install -r requirements.txt

# Tokenizer data required by newspaper3k. Baked into the image (no network at runtime).
RUN /app/venv/bin/python -m nltk.downloader -d /usr/share/nltk_data punkt punkt_tab

# Now copy the application source (changes here don't bust the pip cache above).
COPY apps/scraper ./apps/scraper

# Drop Python caches.
RUN find /app -type d -name __pycache__ -prune -exec rm -rf {} + || true

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runner
LABEL org.opencontainers.image.title="inkbytes-messor-harvester" \
      org.opencontainers.image.source="https://github.com/pragmatalabs/InkBytes"

WORKDIR /app/apps/scraper

ENV PATH="/app/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    NLTK_DATA=/usr/share/nltk_data

# The editable kernel install records the absolute path /app/packages/inkbytes,
# so the venv AND that tree must land at the same paths they had in the builder.
COPY --from=builder /app/venv /app/venv
COPY --from=builder /app/packages /app/packages
COPY --from=builder /app/apps/scraper /app/apps/scraper
COPY --from=builder /usr/share/nltk_data /usr/share/nltk_data

# Runtime dirs are excluded from the image (.dockerignore) and normally
# bind-mounted, but create them so the container also runs standalone — the
# logger opens logs/messor.log eagerly at startup and would crash otherwise.
RUN mkdir -p /app/apps/scraper/logs \
             /app/apps/scraper/data/scrapes \
             /app/apps/scraper/data/history

# FastAPI status/health surface.
EXPOSE 8050

# Scheduled (continuous) mode is the production entrypoint. Container stdin is
# non-interactive, so the harvester runs its cycles and exits the command loop
# cleanly instead of dropping into the REPL (see core/command_processor.py).
# data/ and logs/ are expected to be bind-mounted from the host.
CMD ["python", "main.py", "env.yaml", "--schedule"]
