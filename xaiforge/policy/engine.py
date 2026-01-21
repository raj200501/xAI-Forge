from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from xaiforge.policy.models import PolicyAction, PolicyConfig, PolicyDecision, RiskLevel


class PolicyViolation(Exception):
    def __init__(self, decision: PolicyDecision) -> None:
        super().__init__(decision.reason)
        self.decision = decision


@dataclass
class PolicyReport:
    trace_id: str
    decisions: list[PolicyDecision] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        allowed = sum(1 for decision in self.decisions if decision.allowed)
        denied = sum(1 for decision in self.decisions if decision.action == PolicyAction.DENY)
        monitored = sum(1 for decision in self.decisions if decision.action == PolicyAction.MONITOR)
        return {
            "trace_id": self.trace_id,
            "decisions": len(self.decisions),
            "allowed": allowed,
            "denied": denied,
            "monitored": monitored,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "summary": self.summary(),
            "decisions": [
                {
                    "tool_name": decision.tool_name,
                    "action": decision.action.value,
                    "allowed": decision.allowed,
                    "risk": decision.risk.value,
                    "reason": decision.reason,
                    "matched_rules": list(decision.matched_rules),
                }
                for decision in self.decisions
            ],
        }

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")


class PolicyEngine:
    def __init__(self, config: PolicyConfig) -> None:
        self.config = config
        self._report = PolicyReport(trace_id="")

    @classmethod
    def from_file(cls, path: Path) -> PolicyEngine:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(PolicyConfig.from_dict(payload))

    def attach_trace(self, trace_id: str) -> None:
        self._report.trace_id = trace_id

    def evaluate(self, tool_name: str, args: dict[str, Any]) -> PolicyDecision:
        matched = []
        decisions: list[PolicyDecision] = []
        for rule in self.config.rules:
            if rule.matches(tool_name, args):
                matched.append(rule.name)
                allowed = rule.action in (PolicyAction.ALLOW, PolicyAction.MONITOR)
                decisions.append(
                    PolicyDecision(
                        tool_name=tool_name,
                        action=rule.action,
                        allowed=allowed,
                        risk=rule.risk,
                        reason=rule.reason or f"Rule {rule.name} matched",
                        matched_rules=(rule.name,),
                    )
                )
        if decisions:
            decision = decisions[-1]
        else:
            allowed = self.config.default_action in (PolicyAction.ALLOW, PolicyAction.MONITOR)
            decision = PolicyDecision(
                tool_name=tool_name,
                action=self.config.default_action,
                allowed=allowed,
                risk=self.config.default_risk,
                reason="Default policy applied",
                matched_rules=tuple(matched),
            )
        self._report.decisions.append(decision)
        return decision

    def enforce(self, tool_name: str, args: dict[str, Any]) -> PolicyDecision:
        decision = self.evaluate(tool_name, args)
        if not decision.allowed:
            raise PolicyViolation(decision)
        return decision

    def report(self) -> PolicyReport:
        return self._report


@dataclass(frozen=True)
class PolicySummary:
    tool_name: str
    action: PolicyAction
    risk: RiskLevel
    reason: str


class PolicyAuditor:
    def __init__(self, decisions: Iterable[PolicyDecision]) -> None:
        self._decisions = list(decisions)

    def high_risk(self) -> list[PolicySummary]:
        return [
            PolicySummary(
                tool_name=decision.tool_name,
                action=decision.action,
                risk=decision.risk,
                reason=decision.reason,
            )
            for decision in self._decisions
            if decision.risk == RiskLevel.HIGH
        ]

    def denied(self) -> list[PolicySummary]:
        return [
            PolicySummary(
                tool_name=decision.tool_name,
                action=decision.action,
                risk=decision.risk,
                reason=decision.reason,
            )
            for decision in self._decisions
            if decision.action == PolicyAction.DENY
        ]
