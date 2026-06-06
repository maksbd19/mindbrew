#!/usr/bin/env bash
# Validate Brewmind POC deployment prerequisites.
set -o errexit -o pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ok=0
warn=0

pass() { echo "OK   $*"; ok=$((ok + 1)); }
fail() { echo "FAIL $*"; warn=$((warn + 1)); }

echo "==> Code artifacts"
[[ -f requirements.txt ]] && pass "requirements.txt" || fail "requirements.txt missing"
[[ -f render.yaml ]] && pass "render.yaml" || fail "render.yaml missing"

echo "==> Git"
if git remote get-url origin &>/dev/null; then
  pass "git remote origin configured"
else
  fail "no git remote — push to GitHub before Render/Vercel import"
fi

echo "==> Neon / Postgres"
if [[ -f .env ]] && grep -qE '^DATABASE_URL=.*(neon\.tech|supabase\.co)' .env 2>/dev/null; then
  pass "DATABASE_URL looks like managed Postgres"
elif [[ -n "${DATABASE_URL:-}" ]] && [[ "$DATABASE_URL" == *neon.tech* || "$DATABASE_URL" == *supabase.co* ]]; then
  pass "DATABASE_URL env looks like managed Postgres"
else
  fail "create Neon/Supabase project and set DATABASE_URL (see .env.example)"
fi

echo "==> Render"
if [[ -n "${RENDER_API_KEY:-}" ]]; then
  pass "RENDER_API_KEY set"
else
  fail "deploy via dashboard: New Web Service → connect repo → use render.yaml"
fi

echo "==> Vercel"
if vercel whoami &>/dev/null; then
  pass "vercel CLI authenticated ($(vercel whoami 2>/dev/null))"
else
  fail "run: vercel login"
fi

echo "==> Summary: $ok passed, $warn need attention"
[[ "$warn" -eq 0 ]]
