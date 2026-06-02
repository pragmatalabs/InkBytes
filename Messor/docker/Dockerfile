# Stage 1: Build environment
FROM python:3.11 as builder
LABEL name="inkbytes-messor-harvester-builder2" \
    version="0.1" \
    author="juliandelarosa@icloud.com"

# Install system dependencies for build
RUN apt-get update && apt-get install -y nano git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy application code and requirements
COPY ./ /app

# Prepare necessary directories and scripts
RUN chmod +x /app/scripts/install_inkbytes_libraries.sh && \
    rm -rf /app/venv && \
    python -m venv /app/venv

# Copy configuration and requirements
#COPY ./env.do.yaml /app/env.yaml
#COPY ../requirements.txt /app

# Install application's dependencies
RUN /app/venv/bin/pip install --upgrade pip && \
    /app/venv/bin/pip install -r /app/requirements.txt pytz nltk 'uvicorn[standard]'

# Install libraries from gitlab
RUN for repo in common models database; do \
    /app/scripts/install_inkbytes_libraries.sh https://gitlab.com/inkbytes/${repo}.git develop inkbytes; \
    done

# Clean up any Python cache files (optional)
RUN find /app -type d -name "__pycache__" -exec rm -r {} +
RUN ls -la /app
# Stage 2: Runtime environment
FROM python:3.11 as runner
LABEL name="inkbytes-messor-harvester-runner"

WORKDIR /app

# Copy from builder stage
COPY --from=builder /app /app

# Prepare the environment and set paths
ENV PATH="/app/venv/bin:$PATH"
RUN echo "source /app/venv/bin/activate" > /app/activate_venv.sh && \
    chmod +x /app/scripts/install_inkbytes_libraries.sh /app/activate_venv.sh && \
    echo "source /app/activate_venv.sh" >> /root/.bashrc

# Note: data and logs directories will be mounted as volumes from host
# No need to create them - they will be bound from project root

# Expose the port your app runs on (adjust if needed)
EXPOSE 8080

# Set default command for scheduled mode in Docker
CMD ["python", "main.py", "--schedule"]