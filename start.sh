#!/usr/bin/env bash
# Brewmind one-click local deploy (Docker Compose).
set -o errexit -o pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

COMPOSE=(docker compose)
if ! docker compose version &>/dev/null; then
  COMPOSE=(docker-compose)
fi

usage() {
  cat <<'EOF'
Usage:
  ./start.sh          Build and start Brewmind (foreground)
  ./start.sh stop     Stop all services
  ./start.sh logs     Follow service logs
EOF
}

cmd="${1:-up}"

case "$cmd" in
  stop)
    "${COMPOSE[@]}" down
    echo "Brewmind stopped."
    exit 0
    ;;
  logs)
    exec "${COMPOSE[@]}" logs -f
    ;;
  up|start|"")
    ;;
  -h|--help|help)
    usage
    exit 0
    ;;
  *)
    echo "Unknown command: $cmd" >&2
    usage
    exit 1
    ;;
esac

echo "==> Checking prerequisites..."
./scripts/check-docker-prereqs.sh

ENV_FILE="$ROOT/.env"
ENV_EXAMPLE="$ROOT/.env.example"
PLACEHOLDER_KEY="your_key_from_tokenfactory.nebius.com"

needs_env=false
if [[ ! -f "$ENV_FILE" ]]; then
  needs_env=true
elif grep -qE "^NEBIUS_API_KEY=${PLACEHOLDER_KEY}$" "$ENV_FILE" 2>/dev/null; then
  needs_env=true
elif ! grep -qE '^NEBIUS_API_KEY=.+' "$ENV_FILE" 2>/dev/null; then
  needs_env=true
fi

if [[ "$needs_env" == true ]]; then
  echo
  echo "Brewmind needs a Nebius Token Factory API key for the LLM pipeline."
  echo "Get one at: https://tokenfactory.nebius.com"
  echo
  read -r -s -p "Enter your Nebius API key: " NEBIUS_KEY
  echo
  if [[ -z "$NEBIUS_KEY" || "$NEBIUS_KEY" == "$PLACEHOLDER_KEY" ]]; then
    echo "ERROR: A valid Nebius API key is required." >&2
    exit 1
  fi

  if [[ -f "$ENV_EXAMPLE" ]]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
  else
    touch "$ENV_FILE"
  fi

  if grep -q '^NEBIUS_API_KEY=' "$ENV_FILE"; then
    if [[ "$(uname)" == "Darwin" ]]; then
      sed -i '' "s|^NEBIUS_API_KEY=.*|NEBIUS_API_KEY=${NEBIUS_KEY}|" "$ENV_FILE"
    else
      sed -i "s|^NEBIUS_API_KEY=.*|NEBIUS_API_KEY=${NEBIUS_KEY}|" "$ENV_FILE"
    fi
  else
    echo "NEBIUS_API_KEY=${NEBIUS_KEY}" >> "$ENV_FILE"
  fi

  set_kv() {
    local key="$1"
    local value="$2"
    if grep -q "^${key}=" "$ENV_FILE"; then
      if [[ "$(uname)" == "Darwin" ]]; then
        sed -i '' "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
      else
        sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
      fi
    else
      echo "${key}=${value}" >> "$ENV_FILE"
    fi
  }

  set_kv "DATABASE_URL" "postgresql+psycopg://brewmind:brewmind@postgres:5432/brewmind"
  set_kv "BREWMIND_OFFLINE" "false"
  set_kv "API_URL" "http://api:8000"
  set_kv "NEXT_PUBLIC_API_URL" "/api"
  set_kv "CORS_ORIGINS" "http://localhost:3000,http://127.0.0.1:3000"

  echo "Wrote $ENV_FILE"
fi

echo "==> Building and starting Brewmind..."
"${COMPOSE[@]}" up --build -d

echo "==> Waiting for API health..."
deadline=$((SECONDS + 180))
until curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; do
  if (( SECONDS >= deadline )); then
    echo "ERROR: API did not become healthy in time. Check logs: ./start.sh logs" >&2
    exit 1
  fi
  sleep 3
done

echo "==> Running smoke test..."
API_URL=http://127.0.0.1:8000 ./scripts/poc-smoke-test.sh

echo
echo "Brewmind is running → http://localhost:3000"
echo "API health       → http://localhost:8000/health"
echo
echo "Stop with: ./start.sh stop"
echo "View logs: ./start.sh logs"
