from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Score:
    passed: bool
    reason: str


def score(actual: str, pattern: str) -> Score:
    compiled = re.compile(pattern, re.IGNORECASE | re.DOTALL)
    passed = compiled.search(actual) is not None
    reason = "regex match" if passed else f"pattern {pattern!r} not found"
    return Score(passed=passed, reason=reason)
