#!/usr/bin/env zsh
# Run the Milestone 0 compatibility spike against loopback services only.
set -euo pipefail
setopt null_glob

ROOT=${0:A:h}
ARTIFACTS="$ROOT/artifacts"
RECEIVER_PID=""
MOCK_PID=""
MARGA_PID=""

cleanup() {
  for pid in "$MARGA_PID" "$MOCK_PID" "$RECEIVER_PID"; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
    fi
  done
}
trap cleanup EXIT INT TERM

mkdir -p "$ARTIFACTS"
rm -f "$ARTIFACTS"/*.jsonl "$ARTIFACTS"/*.json "$ARTIFACTS"/*.log

if [[ ! -d "$ROOT/pi-runtime/node_modules" ]]; then
  print -u2 "Run 'npm install' in $ROOT/pi-runtime before starting the spike."
  exit 1
fi

export OTEL_EXPORTER_OTLP_ENDPOINT="http://127.0.0.1:4318"
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT="http://127.0.0.1:4318/v1/traces"
export OTEL_PROPAGATORS="tracecontext"
export KARTA_SPIKE_RESULT_PATH="$ARTIFACTS/pi-result.json"

wait_for_http() {
  local url=$1
  local name=$2
  local attempt=0
  while (( attempt < 80 )); do
    if curl -fsS --max-time 1 "$url" >/dev/null 2>&1; then
      return 0
    fi
    (( attempt += 1 ))
    sleep 0.5
  done
  print -u2 "$name did not become ready at $url"
  return 1
}

cd "$ROOT"
PYTHON="$ROOT/.venv/bin/python"
# Start the server processes directly so cleanup kills the listener itself,
# not a wrapper that leaves an orphaned child holding the port.
"$PYTHON" otlp_receiver.py --output "$ARTIFACTS/spans.jsonl" >"$ARTIFACTS/otlp-receiver.log" 2>&1 &
RECEIVER_PID=$!
"$PYTHON" mock_provider.py --captured-headers "$ARTIFACTS/mock-headers.jsonl" >"$ARTIFACTS/mock-provider.log" 2>&1 &
MOCK_PID=$!
"$PYTHON" instrumented_marga.py --captured-headers "$ARTIFACTS/marga-headers.jsonl" >"$ARTIFACTS/marga.log" 2>&1 &
MARGA_PID=$!

wait_for_http "http://127.0.0.1:4318/health" "OTLP receiver"
wait_for_http "http://127.0.0.1:8091/health" "Mock provider"
wait_for_http "http://127.0.0.1:8011/health" "Marga"

cd "$ROOT/pi-runtime"
npm run --silent run

cd "$ROOT"
uv run python verify_spike.py --artifact-dir "$ARTIFACTS"
