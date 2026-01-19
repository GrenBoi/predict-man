# Builder stage - install dependencies with uv
FROM python:3.12-slim AS builder

# Copy uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies with cache mount
# This layer only rebuilds when pyproject.toml or uv.lock changes
RUN --mount=type=cache,target=/root/.cache/uv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    uv sync --frozen --no-dev


# Runtime stage
FROM python:3.12-slim

# Install cron and curl (for cron job HTTP requests)
RUN apt-get update && \
    apt-get install -y cron curl gosu && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appuser . .

# Set environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Set entrypoint (run as root, will drop privileges for app)
CMD ["uv", "run", "flask", "run", "--port=8000", "--host=0.0.0.0"]
