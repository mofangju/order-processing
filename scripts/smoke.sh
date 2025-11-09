#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(realpath "$0")")/.."

command -v curl >/dev/null 2>&1 || { echo "curl required"; exit 2; }
command -v jq >/dev/null 2>&1 || { echo "jq required"; exit 2; }

HOST_PORT=${HOST_PORT:-9091}

wait_for_url() {
  local url=$1; local timeout=${2:-60}; local interval=2; local elapsed=0
  while true; do
    if curl -s -f "$url" >/dev/null 2>&1; then return 0; fi
    sleep $interval
    elapsed=$((elapsed + interval))
    if [ "$elapsed" -ge "$timeout" ]; then return 1; fi
  done
}

echo "Waiting for services..."
wait_for_url "http://localhost:8000/health" 60 || { echo "Order API not ready"; exit 3; }
wait_for_url "http://localhost:${HOST_PORT}/health" 60 || { echo "Processor not ready"; exit 4; }

echo "Obtaining token..."
TOKEN=$(curl -s -X POST http://localhost:8000/login -H "Content-Type: application/json" -d '{"user_id":"u123","amount":1}' | jq -r .access_token)
[ -n "$TOKEN" ] && [ "$TOKEN" != "null" ] || { echo "Failed to get token"; exit 5; }

echo "Posting order..."
ORDER_RESP=$(curl -s -X POST http://localhost:8000/orders -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"user_id":"u123","amount":999}')
echo "Order response: $ORDER_RESP"

echo "Waiting for metrics..."
for i in {1..15}; do
  if curl -s "http://localhost:${HOST_PORT}/metrics" | grep -q orders_processed_total; then
    echo "Metrics:"
    curl -s "http://localhost:${HOST_PORT}/metrics" | grep orders_processed_total || true
    echo "Smoke tests passed."
    exit 0
  fi
  sleep 2
done

echo "Metrics did not appear in time" >&2
exit 6