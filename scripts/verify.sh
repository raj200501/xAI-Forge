#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN=${PYTHON_BIN:-python}
NODE_BIN=${NODE_BIN:-node}

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python is required but not found. Set PYTHON_BIN or install Python." >&2
  exit 1
fi

$PYTHON_BIN -m pip --version >/dev/null
$PYTHON_BIN -m pip install -e . --no-deps --no-build-isolation

if command -v ruff >/dev/null 2>&1; then
  ruff format --check .
  ruff check .
else
  $PYTHON_BIN -m ruff format --check .
  $PYTHON_BIN -m ruff check .
fi

$PYTHON_BIN -m pytest

if [ -f "web/package.json" ] && command -v "$NODE_BIN" >/dev/null 2>&1; then
  cd web
  if [ -f package-lock.json ]; then
    npm ci
  else
    npm install
  fi
  npm test
  npm run build
  cd "$ROOT_DIR"
fi

SMOKE_DIR="$(mktemp -d)"
trap 'rm -rf "$SMOKE_DIR"' EXIT
$PYTHON_BIN -m xaiforge run --task "Solve 2+2" --root "$SMOKE_DIR" >/dev/null
$PYTHON_BIN -m xaiforge export latest --format markdown >/dev/null
$PYTHON_BIN -m xaiforge eval --dataset trace_ops --gate >/dev/null
$PYTHON_BIN -m xaiforge replay_verify latest >/dev/null
pushd "$SMOKE_DIR" >/dev/null
$PYTHON_BIN -m xaiforge experiment run --mode ab --providers mock --task "verify experiment" >/dev/null
$PYTHON_BIN -m xaiforge perf bench --suite quick --provider mock >/dev/null
$PYTHON_BIN -m xaiforge index build >/dev/null
$PYTHON_BIN -m xaiforge query --fast "type=message" >/dev/null
popd >/dev/null
