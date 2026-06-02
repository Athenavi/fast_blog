# ============================================================================
# FastBlog Multi-Stage Dockerfile
# ============================================================================

# Stage 1: Build Python dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ============================================================================
# Stage 2: Production image
# ============================================================================
FROM python:3.11-slim AS production

LABEL org.opencontainers.image.title="FastBlog"
LABEL org.opencontainers.image.description="Modern, high-performance blog platform"
LABEL org.opencontainers.image.source="https://github.com/Athenavi/fast_blog"
LABEL org.opencontainers.image.licenses="Apache-2.0"

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    ffmpeg \
    tini \
    && rm -rf /var/lib/apt/lists/* \
    && adduser --disabled-password --gecos '' --home /app appuser

# Copy Python packages from builder
COPY --from=builder /install /usr/local

# Fix secure-python-utils broken __init__.py (PasswordService import error)
# The package __init__.py imports PasswordService which doesn't exist in all versions
RUN python -c "from pathlib import Path; \
    p = Path('/usr/local/lib/python3.11/site-packages/secure_python_utils/__init__.py'); \
    p.write_text('# Patched: removed broken PasswordService import to fix startup error\n') if p.exists() else None"

# Create necessary directories BEFORE copying app code (better layer caching)
# IMPORTANT: chown writable directories in the same RUN layer to avoid a separate chown layer
RUN mkdir -p /app/media \
    /app/upload_chunks \
    /app/static \
    /app/themes \
    /app/plugins \
    /app/translations \
    /app/backups \
    /app/logs \
    /app/storage \
    && chown appuser:appuser \
        /app/media \
        /app/upload_chunks \
        /app/static \
        /app/themes \
        /app/plugins \
        /app/translations \
        /app/backups \
        /app/logs \
        /app/storage

# Copy application code as appuser (avoids expensive recursive chown layer)
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 9421

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:9421/api/v1/health || exit 1

# Use tini as init system
ENTRYPOINT ["tini", "--"]

# Start the application
CMD ["python", "main.py", "--backend", "fastapi", "--port", "9421"]
