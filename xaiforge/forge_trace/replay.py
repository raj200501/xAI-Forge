from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from xaiforge.events import RollingHasher
from xaiforge.trace_store import TraceReader


@dataclass
class ReplayResult:
    trace_id: str
    integrity_ok: bool
    expected_hash: str
    computed_hash: str
    event_count: int


def _resolve_latest(root: Path) -> str:
    trace_dir = root / "traces"
    manifests = sorted(trace_dir.glob("*.manifest.json"), key=lambda p: p.stat().st_mtime)
    if not manifests:
        raise FileNotFoundError("No traces found for replay verification.")
    return manifests[-1].stem.replace(".manifest", "")


def verify_trace(root: Path, trace_id: str) -> ReplayResult:
    if trace_id == "latest":
        trace_id = _resolve_latest(root)
    reader = TraceReader(root, trace_id)
    manifest = reader.load_manifest()
    hasher = RollingHasher()
    event_count = 0
    for line in reader.iter_events():
        event = json.loads(line)
        if event.get("type") != "run_end":
            hasher.update(line.strip())
        event_count += 1
    expected_hash = manifest.get("final_hash", "")
    computed_hash = hasher.hexdigest
    integrity_ok = expected_hash == computed_hash
    return ReplayResult(
        trace_id=trace_id,
        integrity_ok=integrity_ok,
        expected_hash=expected_hash,
        computed_hash=computed_hash,
        event_count=event_count,
    )


def replay_summary(result: ReplayResult) -> dict[str, Any]:
    return {
        "trace_id": result.trace_id,
        "integrity_ok": result.integrity_ok,
        "expected_hash": result.expected_hash,
        "computed_hash": result.computed_hash,
        "event_count": result.event_count,
    }
