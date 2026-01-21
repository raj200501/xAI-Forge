#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN=${PYTHON_BIN:-python}
POLICY_PATH="examples/policy-demo.json"

$PYTHON_BIN - <<'PY'
from pathlib import Path
from xaiforge.demo import run_demo

policy_path = Path("examples/policy-demo.json")
result = run_demo(policy_path)
missing = [path for path in [result.export_path, result.bench_path] if not path.exists()]
if missing:
    print("FAIL: missing demo artifacts", missing)
    raise SystemExit(1)
print("PASS: demo completed")
print(f"Trace: {result.trace_id}")
print(f"Export: {result.export_path}")
print(f"Bench: {result.bench_path}")
print(f"Query matches: {result.query_matches}")
print(f"Events: {result.event_count}")
PY
