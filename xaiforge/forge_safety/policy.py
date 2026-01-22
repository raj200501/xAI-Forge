from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from xaiforge.forge_safety.redaction import redact_payload

PolicyAction = Literal["allow", "warn", "block"]


@dataclass(frozen=True)
class PolicyRule:
    name: str
    action: PolicyAction
    tags: list[str]
    contains: list[str]


@dataclass
class PolicyDecision:
    allowed: bool
    action: PolicyAction
    matched_rules: list[str]
    redactions: list[str]


class SafetyPolicy:
    def __init__(self, rules: list[PolicyRule]) -> None:
        self.rules = rules

    def evaluate(self, payload: dict[str, Any]) -> PolicyDecision:
        redacted = redact_payload(payload)
        content = f"{payload} {redacted.payload}"
        matched: list[str] = []
        action: PolicyAction = "allow"
        for rule in self.rules:
            if all(token.lower() in content.lower() for token in rule.contains):
                matched.append(rule.name)
                action = self._promote(action, rule.action)
        allowed = action != "block"
        if action == "block":
            raise ValueError(f"Safety policy blocked request: {matched}")
        return PolicyDecision(
            allowed=allowed,
            action=action,
            matched_rules=matched,
            redactions=redacted.redactions,
        )

    @staticmethod
    def _promote(current: PolicyAction, new: PolicyAction) -> PolicyAction:
        order = {"allow": 0, "warn": 1, "block": 2}
        return new if order[new] > order[current] else current


def default_policy() -> SafetyPolicy:
    rules = [
        PolicyRule(name="block-secrets", action="block", tags=["secret"], contains=["[REDACTED]"]),
        PolicyRule(name="warn-pii", action="warn", tags=["pii"], contains=["@"]),
    ]
    return SafetyPolicy(rules=rules)
