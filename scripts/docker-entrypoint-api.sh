#!/usr/bin/env bash
set -o errexit -o pipefail

cd /app

echo "==> Waiting for PostgreSQL..."
until python - <<'PY'
import os
import psycopg

url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
with psycopg.connect(url, connect_timeout=3):
    pass
PY
do
  sleep 2
done

echo "==> Running database migrations..."
alembic upgrade head

echo "==> Starting API..."
exec "$@"
