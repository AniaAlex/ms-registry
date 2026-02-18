#!/bin/bash
# Generate .env file from Hiera secrets

set -e

DEPLOYMENT_PATH="${DEPLOYMENT_PATH:-/opt/docker-ms-registry}"
ENV_FILE="${DEPLOYMENT_PATH}/.env"

echo "Generating .env from Hiera secrets..."

# Pull secrets from Hiera
SECRET_KEY=$(hiera ms_registry::secret_key)
DB_PASSWORD=$(hiera ms_registry::db_password)
DEBUG=$(hiera ms_registry::debug false)
ENV_NAME=$(hiera ms_registry::env PRODUCTION)
REDIS_URL=$(hiera ms_registry::redis_url redis://redis:6379/0)

# Generate .env file
cat > "${ENV_FILE}" << EOF
# Generated from Hiera on $(date)
ENV=${ENV_NAME}
DEBUG=${DEBUG}
SECRET_KEY=${SECRET_KEY}
DB_PASSWORD=${DB_PASSWORD}
DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@db:5432/ms_registry
REDIS_URL=${REDIS_URL}
EOF

# Secure the file
chmod 600 "${ENV_FILE}"

echo ".env file generated at ${ENV_FILE}"
