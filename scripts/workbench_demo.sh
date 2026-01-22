#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN=${PYTHON_BIN:-python}
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

pushd "$WORK_DIR" >/dev/null
$PYTHON_BIN -m xaiforge experiment run --mode ab --providers mock --task "workbench experiment" >/dev/null
$PYTHON_BIN -m xaiforge perf bench --suite quick --provider mock >/dev/null
$PYTHON_BIN -m xaiforge index build >/dev/null

if $PYTHON_BIN - <<'PY'
import importlib.util

raise SystemExit(0 if importlib.util.find_spec("uvicorn") else 1)
PY
then
$PYTHON_BIN -m xaiforge serve --host 127.0.0.1 --port 8123 >/dev/null 2>&1 &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT
sleep 1
for attempt in {1..10}; do
  if curl -s --fail http://127.0.0.1:8123/api/experiments >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done
curl -s http://127.0.0.1:8123/api/experiments >/dev/null
curl -s http://127.0.0.1:8123/api/reports/perf >/dev/null
kill $SERVER_PID >/dev/null 2>&1 || true
else
$PYTHON_BIN - <<'PY'
from xaiforge.compat.fastapi import TestClient
from xaiforge.server import app

client = TestClient(app)
client.get("/api/experiments")
client.get("/api/reports/perf")
print("Workbench demo used TestClient fallback.")
PY
fi

popd >/dev/null

echo "Workbench demo complete."
echo "Artifacts stored in $WORK_DIR:"
echo "- .xaiforge/experiments"
echo "- reports/experiments"
echo "- reports/perf"
