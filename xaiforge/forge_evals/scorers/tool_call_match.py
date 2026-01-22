from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Score:
    passed: bool
    reason: str


def _normalize(actual: Any) -> dict[str, Any] | None:
    if isinstance(actual, dict):
        return actual
    if isinstance(actual, list) and actual and isinstance(actual[0], dict):
        return actual[0]
    if isinstance(actual, str):
        try:
            data = json.loads(actual)
        except json.JSONDecodeError:
            return None
        return _normalize(data)
    return None


def score(actual: str, expected: dict[str, Any]) -> Score:
    data = _normalize(actual)
    if not data:
        return Score(passed=False, reason="no tool call payload")
    name_match = data.get("name") == expected.get("name")
    args_match = True
    expected_args = expected.get("arguments", {})
    for key, value in expected_args.items():
        if data.get("arguments", {}).get(key) != value:
            args_match = False
            break
    passed = name_match and args_match
    reason = "tool call match" if passed else "tool call mismatch"
    return Score(passed=passed, reason=reason)
