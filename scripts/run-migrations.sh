#!/usr/bin/env bash
# Apply Alembic migrations. Run once before first deploy or after schema changes.
set -o errexit -o pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if command -v uv &>/dev/null; then
  exec uv run alembic upgrade head
fi

exec alembic upgrade head
