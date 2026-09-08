# ==============================================================================
# Athena Document Extractor - Production Dockerfile (Powered by uv & Python 3.13)
# ==============================================================================

# 1. Grab uv binary from official Astral image
FROM ghcr.io/astral-sh/uv:latest AS uv_bin

# 2. Main Application Image matching current uv runtime (Python 3.13)
FROM python:3.13-slim-bookworm

# Copy uv and uvx binaries
COPY --from=uv_bin /uv /uvx /bin/

# Set Python and uv build/runtime environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    HOST=0.0.0.0 \
    PORT=8000 \
    PYTHONPATH=/app

# Install system dependencies
# - tesseract-ocr, tesseract-ocr-ind, tesseract-ocr-eng: OCR engine & language models (Indonesian + English)
# - libgl1, libglib2.0-0, libgomp1: OpenCV & ONNX Runtime CPU dependencies
# - curl, ca-certificates: Container health checking and TLS root certs
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-ind \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root application user and group
RUN groupadd --gid 10001 appgroup && \
    useradd --uid 10001 --gid 10001 --create-home --shell /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy dependency specifications and lockfile first for Docker layer caching
COPY pyproject.toml uv.lock README.md /app/

# Install locked production dependencies into the virtual environment using uv
RUN uv sync --frozen --no-dev --no-install-project

# Copy source code
COPY src /app/src

# Sync and install the project itself
RUN uv sync --frozen --no-dev

# Create runtime directories for logs, trace artifacts, and secrets with non-root ownership
RUN mkdir -p /app/logs /app/trace /app/secrets /app/credentials && \
    chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose service port
EXPOSE 8000

# Container liveness healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# Start FastAPI application via Uvicorn
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
