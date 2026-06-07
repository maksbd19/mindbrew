#!/usr/bin/env bash
# Validate Docker prerequisites for local one-click deploy.
set -o errexit -o pipefail

ok=0
fail=0

pass() { echo "OK   $*"; ok=$((ok + 1)); }
bad() { echo "FAIL $*"; fail=$((fail + 1)); }

if command -v docker &>/dev/null; then
  pass "docker CLI found"
else
  bad "Docker is not installed — install Docker Desktop from https://www.docker.com/products/docker-desktop/"
fi

if docker info &>/dev/null; then
  pass "Docker daemon is running"
else
  bad "Docker daemon is not running — start Docker Desktop and try again"
fi

if docker compose version &>/dev/null; then
  pass "docker compose available"
elif docker-compose version &>/dev/null; then
  pass "docker-compose available"
else
  bad "docker compose is not available"
fi

for f in docker-compose.yml Dockerfile web/Dockerfile scripts/docker-entrypoint-api.sh; do
  if [[ -f "$f" ]]; then
    pass "$f present"
  else
    bad "$f missing"
  fi
done

if [[ -f data/models/iYLI647.xml ]]; then
  pass "bundled GEM model data/models/iYLI647.xml"
else
  bad "data/models/iYLI647.xml missing"
fi

echo "==> Summary: $ok passed, $fail need attention"
[[ "$fail" -eq 0 ]]
