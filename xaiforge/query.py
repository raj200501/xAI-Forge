from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from xaiforge.trace_store import TraceReader, list_manifests


@dataclass(frozen=True)
class Condition:
    field: str
    operator: str
    value: str


def parse_query(expression: str) -> list[Condition]:
    parts = re.split(r"\s+AND\s+", expression, flags=re.IGNORECASE)
    conditions = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if "~" in part:
            field, value = part.split("~", 1)
            operator = "~"
        elif "=" in part:
            field, value = part.split("=", 1)
            operator = "="
        else:
            raise ValueError(f"Invalid query condition: {part}")
        value = value.strip().strip('"').strip("'")
        conditions.append(Condition(field=field.strip(), operator=operator, value=value))
    if not conditions:
        raise ValueError("Query expression is empty")
    return conditions


def query_traces(base_dir: Path, expression: str) -> dict[str, int]:
    conditions = parse_query(expression)
    results: dict[str, int] = {}
    for manifest in list_manifests(base_dir):
        trace_id = manifest.get("trace_id")
        if not trace_id:
            continue
        reader = TraceReader(base_dir, trace_id)
        count = 0
        for line in reader.iter_events():
            if not line.strip():
                continue
            payload = json.loads(line)
            if _matches(payload, manifest, conditions):
                count += 1
        if count:
            results[trace_id] = count
    return results


def _matches(event: dict, manifest: dict, conditions: Iterable[Condition]) -> bool:
    for condition in conditions:
        value = _get_field(event, manifest, condition.field)
        if value is None:
            return False
        if condition.operator == "=":
            if str(value) != condition.value:
                return False
        elif condition.operator == "~":
            if condition.value.lower() not in str(value).lower():
                return False
    return True


def _get_field(event: dict, manifest: dict, field: str) -> str | None:
    alias_map = {
        "tool": "tool_name",
        "task": "task",
    }
    key = alias_map.get(field, field)
    if key in manifest and field == "task":
        return manifest.get(key)
    return event.get(key)
