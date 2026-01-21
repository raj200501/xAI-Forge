from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PolicyAction(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    MONITOR = "monitor"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class PolicyRule:
    name: str
    action: PolicyAction
    tool: str
    arg_patterns: dict[str, str] = field(default_factory=dict)
    risk: RiskLevel = RiskLevel.LOW
    reason: str = ""

    def matches(self, tool_name: str, args: dict[str, Any]) -> bool:
        if self.tool != "*" and self.tool != tool_name:
            return False
        for key, pattern in self.arg_patterns.items():
            value = args.get(key)
            if value is None:
                return False
            if pattern not in str(value):
                return False
        return True


@dataclass(frozen=True)
class PolicyDecision:
    tool_name: str
    action: PolicyAction
    allowed: bool
    risk: RiskLevel
    reason: str
    matched_rules: tuple[str, ...] = ()


@dataclass
class PolicyConfig:
    rules: list[PolicyRule] = field(default_factory=list)
    default_action: PolicyAction = PolicyAction.ALLOW
    default_risk: RiskLevel = RiskLevel.LOW
    description: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> PolicyConfig:
        rules = []
        for raw in payload.get("rules", []):
            rules.append(
                PolicyRule(
                    name=raw.get("name", "rule"),
                    action=PolicyAction(raw.get("action", "allow")),
                    tool=raw.get("tool", "*"),
                    arg_patterns=dict(raw.get("arg_patterns", {})),
                    risk=RiskLevel(raw.get("risk", "low")),
                    reason=raw.get("reason", ""),
                )
            )
        default_action = PolicyAction(payload.get("default_action", "allow"))
        default_risk = RiskLevel(payload.get("default_risk", "low"))
        description = payload.get("description", "")
        return cls(
            rules=rules,
            default_action=default_action,
            default_risk=default_risk,
            description=description,
        )
