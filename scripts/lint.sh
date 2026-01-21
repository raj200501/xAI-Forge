#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN=${PYTHON_BIN:-python}

if command -v ruff >/dev/null 2>&1; then
  ruff check .
else
  $PYTHON_BIN -m ruff check .
fi
