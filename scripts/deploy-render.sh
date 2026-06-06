#!/usr/bin/env bash
# Render full-stack deploy helper for Brewmind.
set -o errexit -o pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Brewmind Render-only deployment"
echo
echo "This repo uses render.yaml as a Blueprint with:"
echo "  - brewmind-db   (Postgres, free tier — expires after 30 days)"
echo "  - brewmind-api  (FastAPI + LangGraph)"
echo "  - brewmind-web  (Next.js frontend)"
echo
echo "Steps:"
echo "  1. Push main to GitHub (if not already)"
echo "  2. Render Dashboard → New → Blueprint"
echo "  3. Connect repo: https://github.com/maksbd19/mindbrew"
echo "  4. Review services, then set secrets on brewmind-api:"
echo "       NEBIUS_API_KEY, NEBIUS_MODEL, NEBIUS_BASE_URL"
echo "  5. Apply Blueprint and wait for all three services to deploy"
echo
echo "Verify after deploy:"
echo "  curl https://brewmind-api.onrender.com/health"
echo "  open https://brewmind-web.onrender.com"
echo
echo "Smoke test (once API URL is live):"
echo "  API_URL=https://brewmind-api.onrender.com ./scripts/poc-smoke-test.sh"
echo

if [[ -n "${API_URL:-}" ]]; then
  echo "==> Running smoke test against $API_URL"
  exec "$ROOT/scripts/poc-smoke-test.sh"
fi
