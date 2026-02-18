#!/usr/bin/env bash

# Start script for MS Registry using Django/uWSGI
set -e

echo "Starting MS Registry Service..."

# Essential environment variables
CONFIG_FILE=${CONFIG_FILE:-/etc/ms-registry/config.yaml}
UWSGI_INI=${UWSGI_INI:-/etc/uwsgi/app.ini}
RUN_MIGRATIONS=${RUN_MIGRATIONS:-true}
COLLECT_STATIC=${COLLECT_STATIC:-true}

# Docker-specific overrides
SERVICE_HOST=${SERVICE_HOST:-0.0.0.0}
SERVICE_PORT=${SERVICE_PORT:-8000}

echo "Configuration:"
echo "  Config File: ${CONFIG_FILE}"
echo "  uWSGI Config: ${UWSGI_INI}"
echo "  Run Migrations: ${RUN_MIGRATIONS}"
echo "  Collect Static: ${COLLECT_STATIC}"
echo "  Service Host: ${SERVICE_HOST}"
echo "  Service Port: ${SERVICE_PORT}"
echo ""

# Wait for database to be ready
if [ -n "${DATABASE_URL}" ] || [ -n "${POSTGRES_HOST}" ]; then
    echo "Waiting for database to be ready..."
    until python manage.py check --database default 2>/dev/null; do
        echo "Database not ready yet, waiting..."
        sleep 2
    done
    echo "Database is ready!"
fi

# Run migrations if enabled
if [ "${RUN_MIGRATIONS}" = "true" ]; then
    echo "Running database migrations..."
    python manage.py migrate --noinput
fi

# Collect static files if enabled
if [ "${COLLECT_STATIC}" = "true" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput
fi

echo "Starting uWSGI server..."
echo "---"

# Execute uWSGI
exec /usr/local/bin/uwsgi --ini "${UWSGI_INI}"
