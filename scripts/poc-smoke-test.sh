#!/usr/bin/env bash
# Smoke-test Brewmind API (local or deployed). Usage:
#   API_URL=https://brewmind-api.onrender.com ./scripts/poc-smoke-test.sh
set -o errexit -o pipefail

API_URL="${API_URL:-http://127.0.0.1:8000}"
API_URL="${API_URL%/}"

echo "==> Health check: $API_URL/health"
health=$(curl -sf "$API_URL/health")
echo "$health" | grep -q '"status"[[:space:]]*:[[:space:]]*"ok"' || {
  echo "FAIL: unexpected health response: $health"
  exit 1
}

echo "==> Create session"
session_json=$(curl -sf -X POST "$API_URL/sessions" \
  -H "Content-Type: application/json" \
  -d '{"raw_brief":"POC smoke test: oleate to wax ester in Yarrowia lipolytica"}')
session_id=$(echo "$session_json" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Session id: $session_id"

echo "==> Poll events (up to 30s)"
deadline=$((SECONDS + 30))
last_seq=0
while (( SECONDS < deadline )); do
  events=$(curl -sf "$API_URL/sessions/$session_id/events?after_seq=$last_seq")
  count=$(echo "$events" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
  if [[ "$count" != "0" ]]; then
    last_seq=$(echo "$events" | python3 -c "import sys,json; xs=json.load(sys.stdin); print(xs[-1]['seq'])")
    echo "  received $count event(s), last_seq=$last_seq"
  fi
  status=$(curl -sf "$API_URL/sessions/$session_id" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
  if [[ "$status" == "awaiting_user" || "$status" == "completed" || "$status" == "failed" ]]; then
    echo "Session reached terminal-ish status: $status"
    break
  fi
  sleep 2
done

echo "==> Smoke test passed"
