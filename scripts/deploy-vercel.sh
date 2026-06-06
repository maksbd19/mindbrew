#!/usr/bin/env bash
# Deploy Brewmind frontend to Vercel. Requires: vercel login, API_URL env var.
set -o errexit -o pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/web"

if [[ -z "${API_URL:-}" ]]; then
  echo "Set API_URL to your Render backend URL before deploying."
  echo "Example: API_URL=https://brewmind-api.onrender.com NEXT_PUBLIC_API_URL=https://brewmind-api.onrender.com ./scripts/deploy-vercel.sh"
  exit 1
fi

export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-$API_URL}"

echo "==> Deploying web/ to Vercel (API_URL=$API_URL)"
vercel deploy --prod \
  --env "API_URL=$API_URL" \
  --env "NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL"
