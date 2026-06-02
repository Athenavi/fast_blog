#!/bin/sh
set -e

# ============================================================================
# FastBlog Docker Entrypoint
# Creates runtime directories with proper permissions, then drops to appuser.
# This handles directories excluded by .dockerignore that the app needs at runtime.
#
# Usage in docker-compose:
#   entrypoint: ["/docker-entrypoint.sh"]
#   user: "0:0"   # start as root so this script can create dirs
# ============================================================================

echo "[entrypoint] Ensuring runtime directories exist..."

# All runtime directories the application may need at startup or runtime
RUNTIME_DIRS="
/app/static_generated
/app/plugins_data
/app/plugins
/app/storage
/app/storage/cache
/app/storage/objects
/app/storage/thumbnails
/app/storage/subscriptions
/app/storage/critical-css
/app/backups
/app/backups/automated
/app/logs
/app/media
/app/uploads
/app/upload_chunks
/app/translations
/app/config
/app/temp
/app/temp/search
/app/custom-patterns
/app/static
/app/static/uploads
/app/static/uploads/mobile
/app/static/uploads/covers
"

# Create all directories
for dir in $RUNTIME_DIRS; do
    [ -z "$dir" ] && continue
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
    fi
done

# Chown everything under /app to appuser (single pass)
chown -R appuser:appuser /app 2>/dev/null || true

echo "[entrypoint] Dropping to appuser and starting application..."

# Drop privileges and execute the original CMD
# Prefer gosu (installed in rebuilt images), fall back to runuser (current image)
if command -v gosu >/dev/null 2>&1; then
    exec tini -- gosu appuser "$@"
else
    exec tini -- runuser -u appuser -- "$@"
fi
