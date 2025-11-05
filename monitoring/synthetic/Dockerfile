FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY synthetic_monitor.py .
COPY config.yml .
COPY schemas/ ./schemas/

# Create non-root user
RUN groupadd -r synthetic && useradd -r -g synthetic synthetic
RUN chown -R synthetic:synthetic /app
USER synthetic

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${METRICS_PORT:-8080}/metrics || exit 1

# Expose metrics port
EXPOSE 8080

# Run the synthetic monitor
CMD ["python", "synthetic_monitor.py"]