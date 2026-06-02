# ============================================================================
# FastBlog Multi-Stage Dockerfile (Optimized for size)
# ============================================================================
# Current: ~1.17GB → Target: ~700MB
# Key optimizations:
#   1. Static ffmpeg binary replaces apt ffmpeg (saves ~270MB of LLVM/Mesa deps)
#   2. pip --no-compile avoids .pyc files
#   3. Clean pip/setuptools/tests/docs from site-packages after install
# ============================================================================

# Stage 1: Build Python dependencies + download static ffmpeg
FROM python:3.14-slim AS builder

WORKDIR /app

# Install build dependencies (no curl needed — ffmpeg is pre-downloaded)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Install static ffmpeg from pre-downloaded tarball (John Van Sickle builds)
# This replaces `apt install ffmpeg` which pulls in 233 packages (~350MB) including
# LLVM (126MB), Mesa GPU (41MB), libz3 (27MB) — none needed in a headless container.
# Pre-downloaded to tools/ffmpeg/ because Docker build network can't reach GitHub.
# To update: download from https://johnvansickle.com/ffmpeg/
COPY tools/ffmpeg/ffmpeg-release-amd64-static.tar.xz /tmp/ffmpeg.tar.xz
RUN tar xJf /tmp/ffmpeg.tar.xz -C /tmp/ && \
    mv /tmp/ffmpeg-*-amd64-static/ffmpeg /usr/local/bin/ffmpeg && \
    mv /tmp/ffmpeg-*-amd64-static/ffprobe /usr/local/bin/ffprobe && \
    chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe && \
    rm -rf /tmp/ffmpeg* && \
    ffmpeg -version | head -1

# Copy and install Python dependencies (--no-compile: skip .pyc, saves ~3MB)
COPY requirements.txt .
RUN pip install --no-cache-dir --no-compile --prefix=/install -r requirements.txt

# ============================================================================
# Stage 2: Production image (minimal runtime)
# ============================================================================
FROM python:3.14-slim AS production

LABEL org.opencontainers.image.title="FastBlog"
LABEL org.opencontainers.image.description="Modern, high-performance blog platform"
LABEL org.opencontainers.image.source="https://github.com/Athenavi/fast_blog"
LABEL org.opencontainers.image.licenses="Apache-2.0"

WORKDIR /app

# Install ONLY essential runtime dependencies (no ffmpeg — using static binary)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    tini \
    gosu \
    && rm -rf /var/lib/apt/lists/* \
    && adduser --disabled-password --gecos '' --home /app appuser

# Copy Python packages from builder, then clean up non-runtime artifacts
COPY --from=builder /install /usr/local

# Clean up: remove pip, setuptools, dist-info, tests, docs, __pycache__
# These are build-time artifacts not needed at runtime (~40MB savings)
RUN find /usr/local/lib/python3.14/site-packages -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null; \
    find /usr/local/lib/python3.14/site-packages -name '*.pyc' -delete 2>/dev/null; \
    rm -rf /usr/local/lib/python3.14/site-packages/pip \
           /usr/local/lib/python3.14/site-packages/pip-*.dist-info \
           /usr/local/lib/python3.14/site-packages/setuptools \
           /usr/local/lib/python3.14/site-packages/setuptools-*.dist-info \
           /usr/local/lib/python3.14/site-packages/_distutils_hack \
           /usr/local/lib/python3.14/site-packages/pkg_resources \
           /usr/local/lib/python3.14/site-packages/wheel \
           /usr/local/lib/python3.14/site-packages/wheel-*.dist-info; \
    find /usr/local/lib/python3.14/site-packages -type d -name 'tests' -exec rm -rf {} + 2>/dev/null; \
    find /usr/local/lib/python3.14/site-packages -type d -name 'test' -exec rm -rf {} + 2>/dev/null; \
    true

# Copy static ffmpeg binaries from builder (replaces apt ffmpeg, ~350MB → ~80MB)
COPY --from=builder /usr/local/bin/ffmpeg /usr/local/bin/ffmpeg
COPY --from=builder /usr/local/bin/ffprobe /usr/local/bin/ffprobe

# Fix secure-python-utils broken __init__.py (PasswordService import error)
RUN python -c "from pathlib import Path; \
    p = Path('/usr/local/lib/python3.14/site-packages/secure_python_utils/__init__.py'); \
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
