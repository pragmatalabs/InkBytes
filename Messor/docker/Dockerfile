# Stage 1: Build environment
FROM python:3.10 as builder
LABEL name="inkbytes-messor-harvester-builder2" \
      version="0.1" \
      author="juliandelarosa@icloud.com"

# Install system dependencies for build
RUN apt-get update && apt-get install -y nano git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy application code and requirements
COPY . /app

# Prepare necessary directories and scripts
RUN mkdir -p /app/data/scrapes_staging_storage/ && \
    chmod +x /app/scripts/install_inkbytes_libraries.sh && \
    rm -rf /app/venv && \
    python3 -m venv /app/venv

COPY ./env.do.yaml /app/env.yaml
COPY ./requirements.txt /app/

# Install application's dependencies
RUN /app/venv/bin/pip install --upgrade pip && \
    /app/venv/bin/pip install -r /app/requirements.txt pytz nltk 'uvicorn[standard]'

# Install libraries from gitlab
RUN for repo in common models database; do \
    /app/scripts/install_inkbytes_libraries.sh https://gitlab.com/inkbytes/${repo}.git develop inkbytes \
    ; done

# Stage 2: Runtime environment
FROM python:3.10-slim as runner
LABEL name="inkbytes-messor-harvester-runner"

WORKDIR /app

# Copy from builder stage
COPY --from=builder /app /app

# Prepare the environment and set paths
ENV PATH="/app/venv/bin:$PATH"
RUN echo "source /app/venv/bin/activate" > /app/activate_venv.sh && \
    chmod +x /app/scripts/install_inkbytes_libraries.sh /app/activate_venv.sh && \
    echo "source /app/activate_venv.sh" >> /root/.bashrc

# Expose the port your app runs on
EXPOSE 8585