# Multi-stage Dockerfile for AlphaTrion Server
# Stage 1: Build stage with uv for fast dependency installation
FROM python:3.12-slim AS builder

# Install uv for faster pip operations
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency files and source code for installation
COPY pyproject.toml README.md ./
COPY alphatrion/ ./alphatrion/

# Install dependencies and package using uv (non-editable for Docker)
RUN uv pip install --system --no-cache .

# Stage 2: Runtime stage
FROM python:3.12-slim

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 alphatrion

# Set working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=alphatrion:alphatrion alphatrion/ ./alphatrion/
COPY --chown=alphatrion:alphatrion migrations/ ./migrations/
COPY --chown=alphatrion:alphatrion alembic.ini ./

# Switch to non-root user
USER alphatrion

# Expose port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run the application
CMD ["alphatrion", "server", "--host", "0.0.0.0", "--port", "8000"]
