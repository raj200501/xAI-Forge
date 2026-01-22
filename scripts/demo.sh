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

$PYTHON_BIN - <<'PY'
import json
from pathlib import Path
import uuid

from xaiforge.forge_evals.runner import run_eval
from xaiforge.forge_gateway import GatewayConfig, ModelGateway
from xaiforge.forge_gateway.models import ModelMessage, ModelRequest
from xaiforge.forge_trace import diff_traces, replay_summary, verify_trace

demo_root = Path("reports/demo")
demo_root.mkdir(parents=True, exist_ok=True)
run_id = uuid.uuid4().hex[:8]

gateway = ModelGateway(config=GatewayConfig())
request = ModelRequest(messages=[ModelMessage(role="user", content="Demo run for gateway")])
import asyncio
result = asyncio.run(gateway.generate(request))
(demo_root / f"gateway_{run_id}.json").write_text(result.response.to_json(), encoding="utf-8")

dataset_path = Path("xaiforge/forge_evals/datasets/trace_ops.jsonl")
report = run_eval(dataset_path, demo_root / "evals")

trace_root = Path(".xaiforge")
latest_manifest = sorted((trace_root / "traces").glob("*.manifest.json"), key=lambda p: p.stat().st_mtime)
if len(latest_manifest) >= 2:
    trace_a = latest_manifest[-1].stem.replace(".manifest", "")
    trace_b = latest_manifest[-2].stem.replace(".manifest", "")
    diff = diff_traces(trace_root, trace_b, trace_a)
    (demo_root / f"diff_{run_id}.json").write_text(json.dumps(diff.to_json(), indent=2), encoding="utf-8")
    (demo_root / f"diff_{run_id}.md").write_text(diff.to_markdown(), encoding="utf-8")
    replay = verify_trace(trace_root, trace_a)
    (demo_root / f"replay_{run_id}.json").write_text(json.dumps(replay_summary(replay), indent=2), encoding="utf-8")

print("DEMO PASSED")
print(f"Gateway response saved under {demo_root}")
print(f"Eval pass rate: {report.pass_rate:.2%}")
PY

$PYTHON_BIN - <<'PY'
import json
from pathlib import Path
import uuid

from xaiforge.forge_experiments.models import ExperimentConfig, ExperimentRequestTemplate
from xaiforge.forge_experiments.runner import run_experiment, save_experiment_artifacts
from xaiforge.forge_gateway.models import ModelMessage
from xaiforge.forge_index.builder import build_index
from xaiforge.forge_perf.runner import run_bench

demo_root = Path("reports/demo")
demo_root.mkdir(parents=True, exist_ok=True)
run_id = uuid.uuid4().hex[:8]

config = ExperimentConfig.create(
    experiment_id=f"demo_exp_{run_id}",
    mode="ab",
    providers=["mock", "mock"],
    request_template=ExperimentRequestTemplate(messages=[ModelMessage(role="user", content="demo")]),
)
result = run_experiment(config)
manifest = save_experiment_artifacts(config, result)
(demo_root / f"experiment_{run_id}.json").write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")

bench = run_bench(suite="quick", provider="mock")
(demo_root / f"perf_{run_id}.json").write_text(json.dumps(bench.to_dict(), indent=2), encoding="utf-8")

stats = build_index(Path(".xaiforge"))
(demo_root / f"index_{run_id}.json").write_text(json.dumps(stats.to_dict(), indent=2), encoding="utf-8")

print("DEMO ARTIFACTS UPDATED")
print(f"Experiment manifest: {manifest.experiment_id}")
print(f"Perf run: {bench.run_id}")
print(f"Index stats: {stats.trace_count} traces")
PY
