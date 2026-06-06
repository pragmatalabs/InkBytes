FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libjpeg-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace/apps/scraper

# Copy the shared kernel package first so the relative -e ../../packages/inkbytes
# editable install in requirements.txt resolves correctly inside the container.
COPY packages /workspace/packages
COPY apps/scraper/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt

COPY apps/scraper /workspace/apps/scraper

# Create dirs that Messor's logging config expects at runtime
RUN mkdir -p /workspace/apps/scraper/logs /workspace/apps/scraper/data/scrapes

CMD ["python", "main.py", "env.yaml", "--schedule"]
