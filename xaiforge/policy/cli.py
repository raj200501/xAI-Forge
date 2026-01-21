from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from xaiforge.policy.models import PolicyAction, PolicyConfig, PolicyRule, RiskLevel


@dataclass(frozen=True)
class PolicySummary:
    description: str
    rules: int
    allow: int
    deny: int
    monitor: int


def load_policy_config(path: Path) -> PolicyConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return PolicyConfig.from_dict(payload)


def summarize_policy(config: PolicyConfig) -> PolicySummary:
    allow = sum(1 for rule in config.rules if rule.action == PolicyAction.ALLOW)
    deny = sum(1 for rule in config.rules if rule.action == PolicyAction.DENY)
    monitor = sum(1 for rule in config.rules if rule.action == PolicyAction.MONITOR)
    return PolicySummary(
        description=config.description or "",
        rules=len(config.rules),
        allow=allow,
        deny=deny,
        monitor=monitor,
    )


def render_policy_summary(summary: PolicySummary) -> str:
    lines = ["Policy summary", ""]
    if summary.description:
        lines.append(f"Description: {summary.description}")
    lines.append(f"Rules: {summary.rules}")
    lines.append(f"- allow: {summary.allow}")
    lines.append(f"- deny: {summary.deny}")
    lines.append(f"- monitor: {summary.monitor}")
    return "\n".join(lines)


def example_policy_rules() -> list[PolicyRule]:
    return [
        PolicyRule(
            name="deny-http",
            action=PolicyAction.DENY,
            tool="http_get",
            risk=RiskLevel.HIGH,
            reason="Network calls are blocked by default.",
        )
    ]
