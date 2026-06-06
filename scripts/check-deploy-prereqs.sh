#!/usr/bin/env bash
# Validate Brewmind hybrid deployment prerequisites.
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
grep -q "uvicorn api.main:app" render.yaml && pass "render.yaml uvicorn start command" || fail "render.yaml missing uvicorn start command"
[[ -x scripts/run-migrations.sh ]] && pass "scripts/run-migrations.sh" || fail "scripts/run-migrations.sh missing"
grep -q "sync: false" render.yaml && pass "render.yaml external DATABASE_URL" || fail "render.yaml DATABASE_URL not sync:false"

echo "==> Git"
if git remote get-url origin &>/dev/null; then
  pass "git remote origin configured"
else
  fail "no git remote — push to GitHub before Render/Vercel import"
fi

echo "==> Supabase"
if [[ -f .env ]] && grep -qE '^DATABASE_URL=.*supabase\.co' .env 2>/dev/null; then
  pass "DATABASE_URL looks like Supabase"
elif [[ -n "${DATABASE_URL:-}" ]] && [[ "$DATABASE_URL" == *supabase.co* ]]; then
  pass "DATABASE_URL env looks like Supabase"
else
  fail "create Supabase project and set DATABASE_URL on Render (see .env.example)"
fi

echo "==> Render"
if [[ -n "${RENDER_API_KEY:-}" ]]; then
  pass "RENDER_API_KEY set"
else
  fail "deploy API: Render Dashboard → New → Blueprint → mindbrew repo"
fi

echo "==> Vercel"
if vercel whoami &>/dev/null; then
  pass "vercel CLI authenticated ($(vercel whoami 2>/dev/null))"
else
  fail "run: vercel login, then API_URL=https://... ./scripts/deploy-vercel.sh"
fi

echo "==> Summary: $ok passed, $warn need attention"
[[ "$warn" -eq 0 ]]
