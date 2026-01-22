from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Score:
    passed: bool
    reason: str


def score(actual: str, expected: str) -> Score:
    passed = actual.strip() == expected.strip()
    reason = "exact match" if passed else f"expected {expected!r} got {actual!r}"
    return Score(passed=passed, reason=reason)
