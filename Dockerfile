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

# Install runtime dependencies (gosu for clean privilege dropping in entrypoint)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    ffmpeg \
    tini \
    gosu \
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
# Create ALL runtime directories that may be excluded by .dockerinclude
# IMPORTANT: chown /app itself so appuser can create new dirs at runtime
RUN mkdir -p /app/media \
    /app/upload_chunks \
    /app/static \
    /app/static/uploads \
    /app/themes \
    /app/plugins \
    /app/plugins_data \
    /app/translations \
    /app/backups \
    /app/backups/automated \
    /app/logs \
    /app/storage \
    /app/storage/cache \
    /app/storage/objects \
    /app/storage/thumbnails \
    /app/uploads \
    /app/config \
    /app/static_generated \
    /app/temp \
    /app/temp/search \
    /app/custom-patterns \
    && chown appuser:appuser \
        /app \
        /app/media \
        /app/upload_chunks \
        /app/static \
        /app/themes \
        /app/plugins \
        /app/plugins_data \
        /app/translations \
        /app/backups \
        /app/logs \
        /app/storage \
        /app/uploads \
        /app/config \
        /app/static_generated \
        /app/temp \
        /app/custom-patterns

# Copy entrypoint script (needs root for directory creation at startup)
# Strip CRLF (Windows line endings) as safety measure for cross-platform builds
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN sed -i 's/\r$//' /docker-entrypoint.sh && chmod +x /docker-entrypoint.sh

# Copy application code as appuser (avoids expensive recursive chown layer)
COPY --chown=appuser:appuser . .

# Expose port
EXPOSE 9421

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:9421/api/v2/health || exit 1

# Entrypoint handles directory creation + privilege dropping to appuser
ENTRYPOINT ["/docker-entrypoint.sh"]

# Start the application
CMD ["python", "main.py", "--backend", "fastapi", "--port", "9421"]
