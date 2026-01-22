from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Score:
    passed: bool
    reason: str


def _shape_matches(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False
        for key, value in expected.items():
            if key not in actual:
                return False
            if not _shape_matches(actual[key], value):
                return False
        return True
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return False
        if not expected:
            return True
        return all(_shape_matches(item, expected[0]) for item in actual)
    return isinstance(actual, type(expected))


def score(actual: str, expected: dict[str, Any]) -> Score:
    try:
        data = json.loads(actual)
    except json.JSONDecodeError:
        return Score(passed=False, reason="invalid JSON")
    passed = _shape_matches(data, expected)
    reason = "schema match" if passed else "schema mismatch"
    return Score(passed=passed, reason=reason)
