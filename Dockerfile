FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 bridge && \
    chown -R bridge:bridge /app

# Copy requirements first for better caching
COPY --chown=bridge:bridge requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=bridge:bridge . .

# Create directory for database with proper permissions
RUN mkdir -p /app/data && chown -R bridge:bridge /app/data

# Switch to non-root user
USER bridge

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    DATABASE_PATH=/app/data/bridge.db

# Expose API port
EXPOSE 8000

# Health check (checks if API is responding)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the API server (which runs the bridge in background)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
