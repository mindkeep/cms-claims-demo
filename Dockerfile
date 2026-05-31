# Build stage — install dependencies
FROM python:3.14-slim AS builder

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install production dependencies only
RUN uv sync --frozen --no-dev

# Runtime stage
FROM python:3.14-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY src/ ./src/
COPY sql/ ./sql/

# Make venv the active Python environment
ENV PATH="/app/.venv/bin:$PATH"

# Create data directories (mounted as volumes in production)
RUN mkdir -p data/raw data/processed data/manifests

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "cms_platform.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
