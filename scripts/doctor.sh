#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN=${PYTHON_BIN:-python}
NODE_BIN=${NODE_BIN:-node}

printf "Doctor report\n\n"

if command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  printf "Python: %s\n" "$($PYTHON_BIN --version 2>&1)"
else
  printf "Python: missing (set PYTHON_BIN or install Python 3.11+)\n"
fi

if command -v "$NODE_BIN" >/dev/null 2>&1; then
  printf "Node: %s\n" "$($NODE_BIN --version)"
else
  printf "Node: missing (install Node 20+)\n"
fi

if command -v npm >/dev/null 2>&1; then
  printf "NPM: %s\n" "$(npm --version)"
else
  printf "NPM: missing (install npm)\n"
fi

if [ -f "pyproject.toml" ]; then
  printf "Python project: pyproject.toml detected\n"
fi

if [ -f "web/package.json" ]; then
  printf "Web app: web/package.json detected\n"
fi

TRACE_DIR="$ROOT_DIR/.xaiforge"
mkdir -p "$TRACE_DIR"
printf "Trace dir: %s\n" "$TRACE_DIR"

printf "\nTips:\n"
printf "- Run scripts/verify.sh for full checks.\n"
printf "- Run scripts/demo.sh for the recruiter demo.\n"
