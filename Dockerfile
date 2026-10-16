# ============================================================================
# FastBlog Multi-Stage Dockerfile
# ============================================================================
# Key points:
#   1. ffmpeg 由 apt 安装（Debian 仓库），构建不再依赖仓库外的二进制包，
#      也就不再需要 BuildKit additional_contexts；代价是镜像比纯静态方案大。
#   2. pip --no-compile avoids .pyc files
#   3. Aggressive cleanup: pip/setuptools/dist-info/tests/docs/include/examples
#   4. Python-based healthcheck eliminates curl dependency
# ============================================================================

# Stage 1: Build Python dependencies
FROM python:3.14-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

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

# Install ONLY essential runtime dependencies
# curl removed: healthcheck uses Python urllib instead (saves ~4MB from curl + deps)
# ffmpeg 走 apt；--no-install-recommends 避免拉入 LLVM / Mesa 等仅在桌面场景需要的推荐依赖
# apt upgrade 确保基础镜像所有预安装包为最新版本
RUN apt-get update && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends \
    libpq5 \
    tini \
    gosu \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && adduser --disabled-password --gecos '' --home /app appuser

# Copy Python packages from builder, then clean up non-runtime artifacts
COPY --from=builder /install /usr/local

# Aggressive cleanup: remove build-time artifacts not needed at runtime
# IMPORTANT: Keep *.dist-info for runtime packages — pydantic uses
# importlib.metadata.version() to check installed package versions at runtime.
# Only remove build-tool dist-info (pip, setuptools, wheel, etc.)
RUN find /usr/local/lib/python3.14/site-packages -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null; \
    find /usr/local/lib/python3.14/site-packages -name '*.pyc' -delete 2>/dev/null; \
    rm -rf /usr/local/lib/python3.14/site-packages/pip \
           /usr/local/lib/python3.14/site-packages/pip-*.dist-info \
           /usr/local/lib/python3.14/site-packages/setuptools \
           /usr/local/lib/python3.14/site-packages/setuptools-*.dist-info \
           /usr/local/lib/python3.14/site-packages/_distutils_hack \
           /usr/local/lib/python3.14/site-packages/pkg_resources \
           /usr/local/lib/python3.14/site-packages/wheel \
           /usr/local/lib/python3.14/site-packages/wheel-*.dist-info \
           /usr/local/lib/python3.14/site-packages/distro-*.dist-info \
           /usr/local/include; \
    find /usr/local/lib/python3.14/site-packages -type d -name 'tests' -exec rm -rf {} + 2>/dev/null; \
    find /usr/local/lib/python3.14/site-packages -type d -name 'test' -exec rm -rf {} + 2>/dev/null; \
    find /usr/local/lib/python3.14/site-packages -type d -name 'examples' -exec rm -rf {} + 2>/dev/null; \
    find /usr/local/lib/python3.14/site-packages -type d -name 'example' -exec rm -rf {} + 2>/dev/null; \
    find /usr/local/lib/python3.14/site-packages -type d -name 'docs' -exec rm -rf {} + 2>/dev/null; \
    true

# Create necessary directories BEFORE copying app code (better layer caching)
# IMPORTANT: chown writable directories in the same RUN layer to avoid a separate chown layer
# Create ALL runtime directories that may be excluded by .dockerignore
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
# tools/ excluded by .dockerignore
COPY --chown=appuser:appuser . .

# Expose port
EXPOSE 9421

# Health check using Python urllib (no curl dependency needed)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9421/api/v3/health')" || exit 1

# Entrypoint handles directory creation + privilege dropping to appuser
ENTRYPOINT ["/docker-entrypoint.sh"]

# Start the application
CMD ["python", "main.py", "--port", "9421"]
