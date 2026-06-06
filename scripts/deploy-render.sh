#!/usr/bin/env bash
# Deploy Brewmind Python API on Render (Supabase Postgres, Vercel frontend).
set -o errexit -o pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Brewmind hybrid deploy: Render API + Supabase + Vercel web"
echo
echo "Architecture:"
echo "  Supabase     Postgres (DATABASE_URL)"
echo "  Render       brewmind-api (FastAPI + LangGraph)"
echo "  Vercel       web/ (Next.js frontend)"
echo
echo "Step 1 — Supabase"
echo "  1. Create project at https://supabase.com"
echo "  2. Settings → Database → Connection string → URI (Direct/Session, port 5432)"
echo "  3. Copy URI for Render DATABASE_URL"
echo
echo "Step 2 — Run migrations (once, before or after first deploy)"
echo "  DATABASE_URL='your-supabase-uri' ./scripts/run-migrations.sh"
echo "  # Or locally: uv run alembic upgrade head"
echo
echo "Step 3 — Render (Python API)"
echo "  1. Render Dashboard → New → Blueprint"
echo "  2. Connect repo: https://github.com/maksbd19/mindbrew"
echo "  3. Set env vars on brewmind-api:"
echo "       DATABASE_URL      Supabase URI"
echo "       NEBIUS_API_KEY    from .env"
echo "       NEBIUS_MODEL      e.g. deepseek-ai/DeepSeek-V4-Pro"
echo "       NEBIUS_BASE_URL   https://api.tokenfactory.nebius.com/v1/"
echo "       CORS_ORIGINS      set after Vercel deploy (e.g. https://your-app.vercel.app)"
echo "  4. Start Command: uvicorn api.main:app --host 0.0.0.0 --port \$PORT"
echo "  5. Apply Blueprint → wait for Live"
echo
echo "Step 4 — Verify API"
echo "  curl https://brewmind-api.onrender.com/health"
echo "  # expected: {\"status\":\"ok\"}"
echo
echo "Step 5 — Vercel (frontend)"
echo "  API_URL=https://brewmind-api.onrender.com ./scripts/deploy-vercel.sh"
echo "  # Vercel Root Directory must be 'web'"
echo "  # Then set CORS_ORIGINS on Render to your Vercel URL"
echo
echo "Smoke test:"
echo "  API_URL=https://brewmind-api.onrender.com ./scripts/poc-smoke-test.sh"
echo

if [[ -n "${API_URL:-}" ]]; then
  echo "==> Running smoke test against $API_URL"
  exec "$ROOT/scripts/poc-smoke-test.sh"
fi
