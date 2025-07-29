FROM ubuntu:22.04

WORKDIR /app

# Set non-interactive installation
ENV DEBIAN_FRONTEND=noninteractive

# Install Python and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set Python as default (if links don't already exist)
RUN if [ ! -e /usr/bin/python ]; then ln -s /usr/bin/python3 /usr/bin/python; fi && \
    if [ ! -e /usr/bin/pip ]; then ln -s /usr/bin/pip3 /usr/bin/pip; fi

# Create a non-root user to run the application
RUN groupadd -r appuser && useradd -r -g appuser -m -d /home/appuser appuser

# Copy pyproject.toml and install dependencies
COPY pyproject.toml .
COPY README.md .

# Install the package in development mode
RUN pip install --no-cache-dir -e .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV AGENT_CONFIG_PATH=/app/config/agents.yaml
ENV LOG_LEVEL=INFO

# Create directories for configuration and logs and set proper permissions
RUN mkdir -p /app/config /app/logs /app/prompts && \
    chown -R appuser:appuser /app

# Copy the rest of the application
COPY agent_builder/ /app/agent_builder/
COPY prompts/ /app/prompts/

# Create config directory if it doesn't exist
RUN mkdir -p /app/config /app/logs

# Copy default config files if available
COPY config/agents.yaml /app/config/ 2>/dev/null || true

# Set proper permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["python", "-m", "agent_builder.cli", "serve", "--config", "/app/config/agents.yaml", "--host", "0.0.0.0", "--port", "5000"]
