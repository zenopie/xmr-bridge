FROM python:3.11-slim

# Install build dependencies and create user
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ make && \
    useradd -m -u 1000 bridge && \
    mkdir -p /app/data && \
    chown -R bridge:bridge /app && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y --auto-remove gcc g++ make

# Copy application code
COPY --chown=bridge:bridge . .

# Switch to non-root user
USER bridge

EXPOSE 8000

# Run the FastAPI application with uvicorn
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]