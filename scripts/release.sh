#!/usr/bin/env bash
set -euo pipefail

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Working tree is dirty. Commit or stash changes first." >&2
  exit 1
fi

echo "Running tests..."
pytest
( cd web && npm test && npm run build )

echo "All checks passed. Remember to bump version + tag release." 
